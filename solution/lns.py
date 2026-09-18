"""Large neighbourhood search over a committed fleet plan -- question 3.

Prioritised planning gives every train an optimal path *given the plans made
before it*, and then never looks back.  Whoever was planned first took the
direct route; everybody after went round.  Measured against a lower bound of
every train running free, that ordering costs about 15% of the sum of costs,
and no amount of care in the initial ordering removes it -- the order is one
guess out of n! and the first guess is rarely the good one.

So stop guessing once.  Repeatedly tear a handful of trains out of the plan and
put them back in a different order; keep the result when it is cheaper, throw
it away when it is not.  Each reinsertion uses the same optimal space-time
search, so every intermediate plan is conflict-free and the whole thing can be
stopped at any moment and still hand back something valid.

The cost being minimised is the one the assignment scores: arrival timesteps
summed over trains, plus twice every timestep past a train's deadline, plus
the episode limit for a train that never arrives at all.

Which trains to pull out matters more than how many.  A train that is running
close to its own shortest path has nothing to gain, so neighbourhoods are seeded
from the train that lost the most time, and filled out with the trains sharing
track with it -- the ones that made it lose that time, and the only ones whose
own plans could make room.
"""

import random
import time
from typing import Dict, List, Sequence, Set, Tuple

from lib_piglet.domains.flatland import UNREACHABLE

from .budget import clock
from .prioritized import FleetPlan

#: LNS should not use one neighbourhood size throughout a run.  Small groups
#: make cheap, local improvements; larger groups are needed to change the
#: ordering through a busy junction.  Cycling these sizes is a deliberately
#: small, dependency-free version of the adaptive-size idea in recent MAPF-LNS
#: work.  The actual size is capped by the number of movable trains.
NEIGHBOURHOOD_SIZES = (4, 8, 12, 16)#goal different for normal LNS

#: A rearrangement is kept whenever the group is cheaper overall, even if it
#: leaves one train worse off than it was.
#:
#: Insisting that no train be made worse -- which this used to -- refuses
#: almost every rearrangement there is: give-way is how a neighbourhood is
#: rearranged at all, and on the 150-train fleets the rule accepted four moves
#: across eight instances against sixteen per instance where it was off. It was
#: put there because give-way plans collapsed under breakdowns, but the cause
#: of the collapses was elsewhere -- a repair with no time left, and the
#: nose-to-nose deadlock in :mod:`solution.replanner` -- and both are fixed at
#: the source now.

#: The Q3 objective is SIC plus twice the total number of delayed timesteps.
#: ``penalties`` is displayed separately by the contest server, which can make
#: it look as if it has already been folded into SIC; it has not.
PENALTY_WEIGHT = 2#goal


def improve(
    plan: FleetPlan, agents: Sequence, seconds: float, seed: int = 0
) -> Tuple[int, int, int]:
    """Spend ``seconds`` making ``plan`` cheaper, in place.

    Returns ``(iterations, accepted, improvement)`` for logging.  ``plan`` is
    left holding the cheapest arrangement found, which is never worse than the
    one it came in with.
    """
    seconds = min(seconds, clock.plan_left())
    if plan.n_agents < 2 or seconds <= 0:
        return (0, 0, 0)

    rng = random.Random(seed)
    # What each train would cost with the railway to itself. A train already
    # running that is not worth tearing out.
    free = [
        plan.goal_distance(
            agent_id,
            plan.domain.state_of(agent.initial_position, agent.initial_direction),
        )
        for agent_id, agent in enumerate(agents)
    ]
    costs = [_agent_cost(plan, agent_id) for agent_id in range(plan.n_agents)]
    best = sum(costs)
    start_total = best
    users = _cell_users(plan)

    deadline = time.perf_counter() + seconds
    iterations = accepted = 0

    while time.perf_counter() < deadline:
        iterations += 1
        size = NEIGHBOURHOOD_SIZES[(iterations - 1) % len(NEIGHBOURHOOD_SIZES)]
        group = _neighbourhood(plan, costs, free, users, rng, size)
        if len(group) < 2:
            continue

        order = _repair_order(plan, group, costs, free, rng)
        saved = {agent_id: plan.paths[agent_id] for agent_id in group}
        for agent_id in group:
            plan.commit(agent_id, [])

        # A completely random repair order throws away the deadline-aware
        # initial plan on every iteration.  Retain urgency as the principal
        # key and randomise only ties, so LNS explores alternatives without
        # repeatedly donating the bottleneck to a train with plenty of slack.
        rebuilt: Dict[int, List[int]] = {}
        ok = True
        for agent_id in order:
            agent = agents[agent_id]
            start_state = plan.domain.state_of(
                agent.initial_position, agent.initial_direction
            )
            states = plan.plan_agent(agent_id, start_state)
            if states is None:
                ok = False
                break
            plan.commit(agent_id, plan.to_positions(states))
            rebuilt[agent_id] = states

        if ok:
            trial = {a: _agent_cost(plan, a) for a in group}
            delta = sum(trial.values()) - sum(costs[a] for a in group)
        else:
            delta = 1  # incomplete: never accepted

        if ok and delta < 0:
            accepted += 1
            best += delta
            for agent_id, cost in trial.items():
                costs[agent_id] = cost
            # The old incremental update only added users.  After enough
            # accepted moves every train appeared to share every cell, so the
            # destroy operator quietly became random.  Rebuild the exact
            # interaction index; it is linear in the current plan and happens
            # only after an improvement.
            users = _cell_users(plan)
        else:
            for agent_id, path in saved.items():
                plan.commit(agent_id, path)

    return (iterations, accepted, start_total - best)

#goal function: SIC + 2* delay
def _agent_cost(plan: FleetPlan, agent_id: int) -> int:
    """What this train's path costs under the assignment's scoring.

    The evaluator charges a train one for every timestep it has not arrived, so
    a path of length L that ends on the target costs L - 1; a train that never
    gets there is charged the whole episode. Lateness is charged again on top,
    at the penalty weight.
    """
    path = plan.paths[agent_id]
    if not path:
        return plan.max_timestep
    width = plan.domain.width_
    if path[-1][0] * width + path[-1][1] != plan.goals[agent_id] >> 2:
        return plan.max_timestep
    arrival = len(path) - 1
    deadline = plan.deadlines[agent_id]
    if deadline is None or arrival <= deadline:
        return arrival
    return arrival + PENALTY_WEIGHT * (arrival - deadline)


def _cell_users(plan: FleetPlan) -> Dict[int, Set[int]]:
    """Which trains run through each cell, for finding trains that interact.

    Built once and updated as the plan changes.  It only steers the choice of
    neighbourhood, so it costs nothing to be a little out of date.
    """
    users: Dict[int, Set[int]] = {}
    for agent_id, cells in enumerate(plan.cells):
        for cell in set(cells):
            users.setdefault(cell, set()).add(agent_id)
    return users


def _neighbourhood(
    plan: FleetPlan,
    costs: Sequence[int],
    free: Sequence[int],
    users: Dict[int, Set[int]],
    rng: random.Random,
    size: int,
) -> List[int]:
    """Pick a handful of trains worth rearranging.

    Seeded from a train that lost time -- chosen at random among the worst, so
    successive iterations do not keep retrying the same one -- and filled out
    with trains that share track with it.  A train running its own shortest
    path already has nothing to give; the ones in its way are where the time
    went.
    """
    seed = _pick_delayed(plan, costs, free, rng)
    if seed is None:
        return []

    # Only trains that have a path are candidates. An empty one is a decision
    # the planner already made -- a train that shares its start cell cannot
    # depart at all, and handing it a path crashes the harness.
    movable = [a for a in range(plan.n_agents) if plan.paths[a]]
    # A small fleet cannot fill a large neighbourhood, and asking it to would
    # never terminate.
    wanted = min(size, len(movable))
    group = {seed}
    cells = plan.cells[seed]
    if cells:
        for _ in range(wanted * 4):
            if len(group) >= wanted:
                break
            sharing = users.get(cells[rng.randrange(len(cells))])
            if sharing:
                candidate = rng.choice(tuple(sharing))
                if plan.paths[candidate]:
                    group.add(candidate)

    # Top up at random when the train runs somewhere quiet.
    for _ in range(wanted * 4):
        if len(group) >= wanted:
            break
        group.add(movable[rng.randrange(len(movable))])
    return list(group)

# urgency differ
def _repair_order(
    plan: FleetPlan,
    group: Sequence[int],
    costs: Sequence[int],
    free: Sequence[int],
    rng: random.Random,
) -> List[int]:
    """Return a deadline-aware, diversified prioritized-planning order.

    Agents which are already late are placed first, followed by those with the
    least free-path deadline slack.  The current excess cost breaks ties before
    a final seeded shuffle, preserving reproducibility while avoiding one fixed
    order becoming a local optimum.
    """
    order = list(group)
    rng.shuffle(order)

    def urgency(agent_id: int) -> Tuple[int, int, int]:
        deadline = plan.deadlines[agent_id]
        if deadline is None:
            return (1, 0, -(costs[agent_id] - free[agent_id]))
        arrival = _arrival_time(plan, agent_id)
        late = max(0, arrival - deadline)
        slack = deadline - free[agent_id]
        return (0 if late else 1, slack, -(costs[agent_id] - free[agent_id]))

    order.sort(key=urgency)
    return order


def _arrival_time(plan: FleetPlan, agent_id: int) -> int:
    """Arrival time used solely to rank a repair order."""
    path = plan.paths[agent_id]
    if not path:
        return plan.max_timestep
    width = plan.domain.width_
    if path[-1][0] * width + path[-1][1] != plan.goals[agent_id] >> 2:
        return plan.max_timestep
    return len(path) - 1


def _pick_delayed(
    plan: FleetPlan, costs: Sequence[int], free: Sequence[int], rng: random.Random
):
    """A train costing more than its journey needs to, or ``None`` if none is.

    Sampled from the worst quarter rather than always taking the very worst:
    the worst train is often the one nothing can be done about, and retrying it
    every iteration would spend the whole budget on it.
    """
    delays = []
    for agent_id in range(plan.n_agents):
        if free[agent_id] >= UNREACHABLE:
            continue
        delay = costs[agent_id] - free[agent_id]
        if delay > 0:
            delays.append((delay, agent_id))
    if not delays:
        return None
    delays.sort(reverse=True)
    return delays[rng.randrange(max(1, len(delays) // 4))][1]
