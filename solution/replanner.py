"""Repairing a committed plan when execution diverges from it -- question 3.

Trains break down.  A malfunctioning train is immobilised where it stands for
between 5 and 15 timesteps, which invalidates its own plan and the plan of
everything queued behind it, and the simulator hands control back to us the
moment it happens.

Replanning the whole fleet each time is not an option: a level 6 episode runs
for 2400 timesteps with 150 trains and breakdowns are frequent, so a full
prioritised pass per breakdown would spend the entire hour-long budget on a
handful of instances.  Instead the repair is *local*.  A train is replanned
only if the breakdown actually invalidates its plan:

* the train that broke down, and any train whose move already failed;
* any train whose committed path runs through a cell that a broken train is
  now going to be sitting in.

Everything else keeps its path, and therefore its reservations, so the
replanned trains have a fixed obstacle field to plan against and the repair
cannot introduce a conflict that was not already there.

The repair proceeds in two phases because a broken train's position is a fact,
not a preference.  Phase one freezes every affected train where it stands for
as long as it is certainly stuck, which both releases the future it can no
longer honour and publishes the cells it is definitely blocking.  Phase two
then replans them in priority order against that.
"""

from collections import deque
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .budget import clock
from .prioritized import FleetPlan

#: Statuses meaning the train is off the map and needs no further planning.
_FINISHED = (2, 3)
#goal
#: How often one train may be displaced within a single repair. Without a cap,
#: two trains in a tight spot take turns bumping each other indefinitely.
MAX_BUMPS_PER_TRAIN = 2

#: How many times one train may bump other trains out of the way before we
#: settle for a looser plan. Three rounds clears the head-on cases; letting it
#: run further mostly just replans the whole fleet by another name.
MAX_ESCALATIONS = 3

#: How far ahead to look for trains that have booked the cell this one is
#: standing on. Those are what stop a boxed-in train from simply waiting.
WAIT_LOOKAHEAD = 32

#: Ceiling on how many trains one repair will plan, displacements included.
#: Parking a train requeues everything routed through the cell it parks on, and
#: those trains can park in turn, so the queue can feed itself -- one instance
#: sat in a single repair call for ten minutes before this cap existed. A
#: repair that has grown this large has stopped being a local repair. Whatever
#: is still queued is parked, which is always safe, and picked up again by the
#: next repair.
WORK_BUDGET = 64


def repair(
    plan: FleetPlan,
    agents: Sequence,
    current_timestep: int,
    new_malfunction_agents: Iterable[int],
    failed_agents: Iterable[int],
) -> None:
    """Bring ``plan`` back in line with what the simulator actually did."""
    domain = plan.domain
    now = current_timestep

    if clock.spent():
        # Out of time. Doing nothing is safe: where a path no longer matches
        # where its train is, the harness cannot derive a move and issues a
        # stop. A poor score beats an instance that never finishes.
        return

    holds = _holds(agents)
    dirty = _affected(plan, agents, now, holds, new_malfunction_agents, failed_agents)
    if not dirty:
        return

    # Phase one: freeze. Each affected train is pinned to where it actually is
    # for as long as its malfunction lasts, which drops the reservations it can
    # no longer keep and claims the cells it is certainly occupying.
    for agent_id in dirty:
        if _is_parked(plan, agent_id):
            # Already spelled out as standing still, with nothing reserved past
            # where it stands. Re-freezing it would rewrite a path as long as
            # the episode, once per timestep, for every parked train -- which
            # is quadratic in the episode length and was enough on its own to
            # stall an instance for minutes.
            continue
        _freeze(plan, agents, agent_id, now, holds[agent_id])

    # Phase two: replan, tightest schedules first, against everything that was
    # left alone plus the freezes above.
    rank = _ranking(plan)
    queue = deque(sorted(dirty, key=lambda a: rank[a]))
    queued = set(dirty)
    # A train may be bumped out of the way a couple of times, no more: without
    # a cap two trains in a tight spot can take turns displacing each other for
    # as long as we let them.
    bumps: Dict[int, int] = {}
    work = 0
    # Out of time is handled like out of budget: stop searching and park what is
    # left. A parked train scores badly; an instance that never finishes scores
    # nothing, and takes the rest of the question down with it.
    while queue and work < WORK_BUDGET and not clock.spent():
        agent_id = queue.popleft()
        queued.discard(agent_id)
        work += 1
        agent = agents[agent_id]
        position = (int(agent.position[0]), int(agent.position[1]))
        start_state = domain.state_of(position, agent.direction)
        hold = holds[agent_id]

        states = _plan_with_escalation(
            plan, agents, agent_id, start_state, now, hold, holds, bumps, queue, queued
        )

        if states is None:
            if _is_parked(plan, agent_id):
                continue  # already parked here; its path still says so
            # Park it where it stands. Every train already routed through this
            # cell has to be found first, before the claim overwrites theirs in
            # the reservation table -- that check is what the plan's
            # consistency now rests on, so it ignores the bump cap.
            plan.stalled.add(agent_id)
            for other in _claimants(plan, agents, start_state >> 2, now, queued):
                bumps[other] = bumps.get(other, 0) + 1
                _freeze(plan, agents, other, now, holds[other])
                queued.add(other)
                queue.append(other)
            states = plan.hold_states(start_state, now)
        else:
            plan.stalled.discard(agent_id)

        prefix = _prefix(plan, agent_id, now, position)
        plan.commit(agent_id, prefix + plan.to_positions(states))

    # Out of budget or out of time with trains still queued. They are frozen,
    # and a frozen path stops at the freeze -- which the simulator reads as "do
    # nothing", which a moving train takes as "carry on forward". Parking
    # spells the standing still out, and the next repair picks them up again.
    for agent_id in queue:
        if _is_parked(plan, agent_id):
            continue
        agent = agents[agent_id]
        position = (int(agent.position[0]), int(agent.position[1]))
        start_state = domain.state_of(position, agent.direction)
        plan.stalled.add(agent_id)
        prefix = _prefix(plan, agent_id, now, position)
        plan.commit(
            agent_id,
            prefix + plan.to_positions(plan.hold_states(start_state, now)),
        )


def _plan_with_escalation(
    plan: FleetPlan,
    agents: Sequence,
    agent_id: int,
    start_state: int,
    now: int,
    hold: int,
    holds: Sequence[int],
    bumps: Dict[int, int],
    queue: "deque[int]",
    queued: Set[int],
) -> Optional[List[int]]:
    """Find this train something to do, loosening the problem until one exists.

    The rungs, in order of how much they give away:

    1. a conflict-free plan around every reservation there is;
    2. the same, after bumping the trains that booked the track it needs and
       queueing them to be replanned in turn -- otherwise a pair of trains
       grinds against each other for the rest of the episode, calling replan
       on every timestep and arriving never;
    3. a plan that is allowed to arrive after the episode ends, so the train at
       least keeps moving towards its goal and out of the way.

    ``None`` means none of them fit and the caller should park the train.

    Every rung is conflict-free against the whole plan.  Nothing on this ladder
    is allowed to be optimistic about the future, and that restraint is what
    the ladder is really about.  There used to be a rung between 2 and 3 that
    honoured reservations for the next 64 timesteps and ignored them beyond --
    reasonable on its face, since a repair would come along long before the
    optimistic part was reached.  What actually happened is that two trains
    each got one and drove into each other: on single track a nose-to-nose pair
    can never be separated, because neither can pass and neither can reverse
    anywhere but a dead end.  Dropping the rung was worth two trains, 0.5% of
    the final SIC and 18% of the penalty, and left every train on the local set
    arriving.
    """
    states = plan.plan_agent(agent_id, start_state, start_time=now, hold=hold)

    for _ in range(MAX_ESCALATIONS):
        if states is not None:
            return states
        bumped = _blockers(plan, agents, agent_id, start_state, now, hold, bumps)
        if not bumped:
            break
        for other in bumped:
            bumps[other] = bumps.get(other, 0) + 1
            _freeze(plan, agents, other, now, holds[other])
            if other not in queued:
                queued.add(other)
                queue.append(other)
        states = plan.plan_agent(agent_id, start_state, start_time=now, hold=hold)

    if states is None:
        states = plan.plan_agent(
            agent_id, start_state, start_time=now, hold=hold, on_time=False
        )
    return states


def _claimants(
    plan: FleetPlan, agents: Sequence, cell: int, now: int, queued: Set[int]
) -> List[int]:
    """Trains whose committed path still runs through ``cell`` after ``now``."""
    table = plan.table
    found: List[int] = []
    seen: Set[int] = set(queued)
    for time in range(now + 1, table.horizon + 1):
        other = table.occupant(cell, time)
        if other is None or other in seen:
            continue
        seen.add(other)
        if agents[other].status not in _FINISHED and agents[other].position is not None:
            found.append(other)
    return found


def _is_parked(plan: FleetPlan, agent_id: int) -> bool:
    """Is this train already committed to standing still for the whole episode?"""
    return (
        agent_id in plan.stalled
        and len(plan.paths[agent_id]) >= plan.max_timestep
    )


def _freeze(plan: FleetPlan, agents: Sequence, agent_id: int, now: int, hold: int) -> None:
    """Pin a train to where it is for as long as it is certainly stuck."""
    agent = agents[agent_id]
    position = (int(agent.position[0]), int(agent.position[1]))
    prefix = _prefix(plan, agent_id, now, position)
    plan.commit(agent_id, prefix + [position] * (hold + 1))


def _blockers(
    plan: FleetPlan,
    agents: Sequence,
    agent_id: int,
    start_state: int,
    now: int,
    hold: int,
    bumps: Dict[int, int],
) -> List[int]:
    """Trains standing between this one and its goal, in space and time.

    Two groups matter.  Trains that have booked the cell this one is *standing
    on* are the reason it cannot even wait where it is, which is what usually
    leaves a train with no legal move at all.  Trains that have booked cells
    along its unobstructed shortest path are the reason it cannot leave.

    Trains that have already been bumped their fill are left out, so the
    escalation cannot chase its own tail around a cluster.
    """
    table = plan.table
    blockers: List[int] = []
    seen: Set[int] = {agent_id}

    def consider(other: Optional[int]) -> None:
        if other is None or other in seen:
            return
        seen.add(other)
        if bumps.get(other, 0) >= MAX_BUMPS_PER_TRAIN:
            return
        if agents[other].status not in _FINISHED and agents[other].position is not None:
            blockers.append(other)

    here = start_state >> 2
    for time in range(now + hold + 1, now + hold + 1 + WAIT_LOOKAHEAD):
        consider(table.occupant(here, time))

    states = plan.domain.shortest_path(start_state, plan.goals[agent_id])
    if states is not None:
        time = now + hold
        previous: Optional[int] = None
        for state in states:
            cell = state >> 2
            consider(table.occupant(cell, time))
            if previous is not None and previous != cell:
                consider(table.swap_partner(previous, cell, time))
            previous = cell
            time += 1
    return blockers


def _holds(agents: Sequence) -> List[int]:
    """How many further timesteps each train is unable to move for.

    The simulator decrements the counter at the end of the step it broke in, so
    the value read here is exactly the number of *upcoming* timesteps the train
    has to sit out -- it may move again on the step after that.
    """
    return [int(agent.malfunction_data.get("malfunction", 0)) for agent in agents]


def _affected(
    plan: FleetPlan,
    agents: Sequence,
    now: int,
    holds: Sequence[int],
    new_malfunction_agents: Iterable[int],
    failed_agents: Iterable[int],
) -> List[int]:
    """Which trains need a new path, seeds plus everything they now block."""
    dirty: Set[int] = set()
    # Parked trains join every repair: parking is what we do when a train has
    # nothing legal left, and the point of retrying is that the railway around
    # it keeps changing.
    seeds = list(new_malfunction_agents) + list(failed_agents) + list(plan.stalled)
    for agent_id in seeds:
        agent = agents[agent_id]
        if agent.status not in _FINISHED and agent.position is not None:
            dirty.add(agent_id)
        else:
            plan.stalled.discard(agent_id)

    # A train that stops moving keeps a cell somebody else had booked. Ask the
    # reservation table who that is, before phase one overwrites the answer.
    table = plan.table
    width = plan.domain.width_
    for agent_id in list(dirty):
        hold = holds[agent_id]
        if hold <= 0:
            continue
        agent = agents[agent_id]
        cell = int(agent.position[0]) * width + int(agent.position[1])
        for time in range(now + 1, now + hold + 1):
            other = table.occupant(cell, time)
            if other is not None and other != agent_id:
                if agents[other].status not in _FINISHED and agents[other].position is not None:
                    dirty.add(other)
    return list(dirty)


def _prefix(plan: FleetPlan, agent_id: int, upto: int, fill: Tuple[int, int]) -> List[Tuple[int, int]]:
    """The part of a train's path that has already been executed.

    The simulator reads a path positionally, so a repaired path has to keep its
    timesteps lined up: everything before ``upto`` is history and is carried
    over untouched (padded, if the old path had already run out).
    """
    old = plan.paths[agent_id]
    if len(old) >= upto:
        return list(old[:upto])
    return list(old) + [fill] * (upto - len(old))


def _ranking(plan: FleetPlan) -> List[int]:
    """Position of each train in the priority order, for cheap sorting."""
    rank = [0] * plan.n_agents
    for position, agent_id in enumerate(plan.order):
        rank[agent_id] = position
    return rank
