"""Prioritised planning for a whole fleet -- question 3.

Every train is under our control here, so unlike question 2 we choose the order
they are planned in.  Trains are planned one at a time, each treating the plans
already made as moving obstacles; the resulting plan is conflict-free by
construction, and each path comes from the same optimal space-time search that
question 2 uses.

Prioritised planning is incomplete: a train planned late can find itself boxed
in.  That matters more in Flatland than on an open grid, because every train is
placed on its start cell at timestep 0 and single track gives it nowhere to
step aside.  :func:`plan_fleet` therefore reshuffles the order rather than
giving up, and question 3's ``replan`` is there to repair what execution breaks
anyway.

The priority order is what the whole thing turns on.  Trains are ordered by
*slack*, how much spare time they have between the shortest journey they could
possibly make and the deadline they are judged against: the tightest schedule
gets first pick of the railway, which is precisely where a delay would cost
penalty points.
"""

import random
from typing import Dict, List, Optional, Sequence, Set, Tuple

from lib_piglet.domains.flatland import UNREACHABLE, flatland_domain

from .budget import clock
from .reservation import ReservationTable
from .search import find_timed_path

#: Timesteps a train stands still for when the planner has nothing better for
#: it to do.
#:
#: It used to be the rest of the episode, which is simple and wrong: a parked
#: train reserves its cell for every timestep that is left, so it stops being a
#: train that could not be routed and becomes a wall. Trains routed through
#: that cell are turned back, some of them park in turn, and on a single-track
#: map the walls end up facing each other with no way past. Parking for a
#: while instead says the only thing that is actually known -- that the train
#: is not moving yet -- and the repair that follows the expiry gets to try
#: again with whatever the railway looks like by then.
PARK_HORIZON = 32


class FleetPlan:
    """The committed path of every train, and the reservations they imply.

    The plan is mutable and long-lived: ``question3.replan`` repairs it in
    place, so committing a new path for one train has to leave the other
    trains' reservations untouched.
    """

    __slots__ = (
        "domain",
        "max_timestep",
        "n_agents",
        "paths",
        "cells",
        "table",
        "goals",
        "deadlines",
        "order",
        "stalled",
        "banned",
        "retry_after",
    )

    def __init__(self, domain: flatland_domain, agents: Sequence, max_timestep: int):
        self.domain = domain
        self.max_timestep = max_timestep
        self.n_agents = len(agents)
        self.paths: List[List[Tuple[int, int]]] = [[] for _ in agents]
        self.cells: List[List[int]] = [[] for _ in agents]
        self.table = ReservationTable(domain.n_cells_)
        self.goals = [domain.goal_state(agent.target) for agent in agents]
        self.deadlines = [agent.deadline for agent in agents]
        self.order: List[int] = list(range(len(agents)))
        #: Trains parked because nothing legal was left for them to do. They
        #: are retried on every repair until one of them takes.
        self.stalled: Set[int] = set()
        #: Rail states no train may plan into, because a train that has stopped
        #: for good is sitting in the only cell they lead to. Recomputed by
        #: every repair from the trains that are currently parked; empty for
        #: the initial plan, where nothing has stopped yet.
        self.banned: Set[int] = set()
        #: Train -> the timestep before which retrying it is not worth a
        #: search. A parked train is retried because the railway around it
        #: keeps changing, but it does not change every timestep.
        self.retry_after: Dict[int, int] = {}

    def goal_distance(self, agent_id: int, state: int) -> int:
        """Exact remaining journey for one train from one state."""
        return self.domain.goal_distances(self.goals[agent_id])[state]

    def reset(self) -> None:
        """Forget every committed path, ready for another planning pass."""
        self.paths = [[] for _ in range(self.n_agents)]
        self.cells = [[] for _ in range(self.n_agents)]
        self.table = ReservationTable(self.domain.n_cells_)
        self.stalled = set()
        self.banned = set()
        self.retry_after = {}

    def commit(self, agent_id: int, positions: List[Tuple[int, int]]) -> None:
        """Make ``positions`` this train's path, replacing whatever it had.

        The reservation table is rewritten for the whole path rather than the
        changed tail.  A swap prohibition is derived from a *pair* of
        consecutive cells, so splicing the tail alone would leave the
        prohibition that straddles the splice point behind; rewriting the lot
        is a few hundred dictionary operations and is obviously correct.
        """
        table = self.table
        old = self.cells[agent_id]
        if old:
            table.remove_path(agent_id, old)
        width = self.domain.width_
        cells = [p[0] * width + p[1] for p in positions]
        self.paths[agent_id] = positions
        self.cells[agent_id] = cells
        table.add_path(agent_id, cells)

    def plan_agent(
        self,
        agent_id: int,
        start_state: int,
        start_time: int = 0,
        hold: int = 0,
        horizon: Optional[int] = None,
        on_time: bool = True,
        avoid_traps: bool = True,
        budget: Optional[int] = None,
    ) -> Optional[List[int]]:
        """Conflict-free states for one train, or ``None`` if there are none.

        ``horizon`` limits how far ahead reservations are honoured, and
        ``on_time`` can be dropped to let the train arrive after the episode's
        last timestep -- a late arrival is worth nothing itself, but a train
        still heading for its goal keeps out of the way better than one that
        has given up.  ``avoid_traps`` can be dropped to let the train plan
        into a dead end behind a stopped train, which is the last thing to try
        before parking it.  ``budget`` overrides how many expansions the search
        may spend.
        """
        return find_timed_path(
            self.domain,
            start_state,
            self.goals[agent_id],
            self.table,
            start_time=start_time,
            hold=hold,
            latest_arrival=(self.max_timestep - 1) if on_time else None,
            horizon=horizon,
            banned=self.banned if avoid_traps else None,
            **({} if budget is None else {"budget": budget}),
        )

    def fallback_states(
        self, agent_id: int, start_state: int, start_time: int = 0, hold: int = 0
    ) -> List[int]:
        """A path to fall back on when no conflict-free one can be found.

        Used only for the initial fleet plan, where a train that never sets off
        is worth ``T_max`` for certain.  Question 3 calls ``replan`` the moment
        a move fails, so a train that starts out on a colliding path gets
        repaired the first time it actually gets in somebody's way, having in
        the meantime made progress.

        Returns the train's own shortest path, or a plan to sit still if even
        that does not exist.
        """
        states = self.domain.shortest_path(start_state, self.goals[agent_id])
        if states is None:
            # The goal is unreachable on this railway; hold position for the
            # whole episode, because no later repair can change that.
            return self.hold_states(start_state, start_time, self.max_timestep)
        return [start_state] * hold + states

    def hold_states(
        self, start_state: int, start_time: int, horizon: int = PARK_HORIZON
    ) -> List[int]:
        """Stand a train still where it is, for ``horizon`` timesteps.

        The standing still has to be spelled out rather than the path simply
        ending: an exhausted path makes the simulator issue "do nothing", and a
        train that was moving treats that as "carry on forward". Repeating the
        cell is what tells it to stand still -- and the repetition has to run to
        at least two, because the first one is what the simulator reads as a
        stop and only after that is "do nothing" safe.

        Pass ``horizon=self.max_timestep`` for a train that is never going
        anywhere -- one whose goal is not reachable on this railway at all --
        where there is nothing to be gained by being asked about it again.
        """
        remaining = self.max_timestep - start_time
        return [start_state] * max(2, min(horizon, remaining))

    def to_positions(self, states: Sequence[int]) -> List[Tuple[int, int]]:
        """``(x, y)`` path for a state sequence."""
        position_of = self.domain.position_of
        return [position_of(state) for state in states]


def priority_order(plan: FleetPlan, agents: Sequence) -> List[int]:
    """Rank trains by how little slack their schedule leaves them.

    Slack is the deadline minus the shortest journey the train could possibly
    make.  A train with none of it will be penalised for every timestep it is
    made to wait, so it is planned first and gets the free railway; a train
    with hours to spare can afford the detours.  On the largest fleets the
    absolute deadline is the first key instead: those instances have enough
    traffic that clearing early-deadline trains before the rush lowers the
    executed SIC even when a few more trains miss the deadline.  Ties -- and
    trains with no deadline -- fall back on the longer journey first, which is
    the usual prioritised-planning tie-break: long paths are the hardest to fit
    in and are best placed while the map is still empty.
    """
    domain = plan.domain
    ranked = []
    for agent_id, agent in enumerate(agents):
        state = domain.state_of(agent.initial_position, agent.initial_direction)
        shortest = plan.goal_distance(agent_id, state)
        if shortest >= UNREACHABLE:
            # Hopeless trains are planned last: they cannot arrive whatever we
            # do, so they should not be taking track off trains that can.
            ranked.append((1, 0, 0, agent_id))
            continue
        deadline = plan.deadlines[agent_id]
        slack = (deadline - shortest) if deadline is not None else UNREACHABLE
        if plan.n_agents >= 100:
            ranked.append((0, deadline, slack, -shortest, agent_id))
        else:
            ranked.append((0, slack, -shortest, agent_id))
    ranked.sort()
    return [entry[-1] for entry in ranked]


#: Keep one stable initial priority order.  Multi-start selection based only
#: on static paths looked cheaper but was less robust to the recorded Q3
#: malfunctions, causing many more trains to fail during execution.
INITIAL_ORDERS = 1


def _cannot_depart(agents: Sequence) -> Set[int]:
    """Trains that will still be off the map after timestep 0, and always will.

    Every train is placed on its start cell at timestep 0 and never gets
    another chance -- the harness only issues the departure command on that one
    timestep. When two trains share a start cell the simulator gives it to the
    lower-numbered one, and the other is left with no position at all.

    Handing such a train a path is not merely wasted, it is fatal: the harness
    asks the simulator for the action that moves it from a position it does not
    have, and the assertion that fails takes the whole evaluation process with
    it -- our own error handling never sees it, because the failure is on the
    harness's side of the call. The assignment's own instances all give every
    train its own start cell, but a generated one need not, and one crash costs
    a whole question rather than one instance.
    """
    claimed = {}
    blocked = set()
    for agent_id, agent in enumerate(agents):
        cell = (int(agent.initial_position[0]), int(agent.initial_position[1]))
        if cell in claimed:
            blocked.add(agent_id)
        else:
            claimed[cell] = agent_id
    return blocked


def plan_fleet(plan: FleetPlan, agents: Sequence, rounds: int = INITIAL_ORDERS) -> None:
    """Choose the best of a few deadline-aware global priority orders.

    Prioritized planning used to stop at its first all-feasible order.  That
    avoids collisions but leaves its entire deadline schedule to one arbitrary
    ordering.  Evaluate a small, deterministic portfolio instead: the normal
    slack order, an earliest-deadline order, and a locally perturbed version of
    the normal order.  Failed plans are always dominated by feasible ones; ties
    are decided by the exact Q3 static objective.
    """
    grounded = _cannot_depart(agents)
    base = [a for a in priority_order(plan, agents) if a not in grounded]
    orders = _candidate_orders(plan, agents, base, rounds)
    best_paths = None
    best_key = None
    best_order = base

    for order in orders:
        if clock.plan_left() <= 0:
            break
        plan.reset()
        failures = _planning_pass(plan, agents, order)
        key = (len(failures), _static_objective(plan))
        if best_key is None or key < best_key:
            best_paths = [path[:] for path in plan.paths]
            best_key = key
            best_order = order
        if clock.plan_left() <= 0:
            break

    # Restore the winning candidate, because the final candidate examined is
    # not necessarily the cheapest one.
    if best_paths is not None:
        plan.reset()
        for agent_id, path in enumerate(best_paths):
            plan.commit(agent_id, path)
    plan.order = best_order


def _candidate_orders(
    plan: FleetPlan, agents: Sequence, base: Sequence[int], limit: int
) -> List[List[int]]:
    """A compact portfolio of complementary, reproducible priority orders."""
    orders = [list(base)]
    if limit <= 1:
        return orders

    domain = plan.domain

    def deadline_key(agent_id: int) -> Tuple[int, int, int, int]:
        agent = agents[agent_id]
        state = domain.state_of(agent.initial_position, agent.initial_direction)
        shortest = plan.goal_distance(agent_id, state)
        deadline = plan.deadlines[agent_id]
        if deadline is None:
            return (1, UNREACHABLE, -shortest, agent_id)
        return (0, deadline, deadline - shortest, -shortest)

    orders.append(sorted(base, key=deadline_key))
    if limit <= 2:
        return orders

    # Preserve broad priority bands but explore different give-way decisions
    # within them.  This is intentionally seeded from map-independent input so
    # identical submissions remain reproducible.
    rng = random.Random(len(base) * 1_000_003 + plan.max_timestep)
    rank = {agent_id: position for position, agent_id in enumerate(base)}
    span = max(2, len(base) // 12)
    noise = {agent_id: rng.uniform(-span, span) for agent_id in base}
    orders.append(sorted(base, key=lambda a: (rank[a] + noise[a], a)))
    return orders[:limit]


def _static_objective(plan: FleetPlan) -> int:
    """The contest objective of a plan before malfunctions occur."""
    total = 0
    width = plan.domain.width_
    for agent_id, path in enumerate(plan.paths):
        if not path or path[-1][0] * width + path[-1][1] != plan.goals[agent_id] >> 2:
            total += plan.max_timestep
            continue
        arrival = len(path) - 1
        deadline = plan.deadlines[agent_id]
        total += arrival if deadline is None else arrival + 2 * max(0, arrival - deadline)
    return total


def _planning_pass(plan: FleetPlan, agents: Sequence, order: Sequence[int]) -> List[int]:
    """Plan every train once in ``order``; return those that had to fall back."""
    domain = plan.domain
    failures: List[int] = []
    for agent_id in order:
        agent = agents[agent_id]
        start_state = domain.state_of(agent.initial_position, agent.initial_direction)
        states = plan.plan_agent(agent_id, start_state)
        if states is None:
            states = plan.fallback_states(agent_id, start_state)
            failures.append(agent_id)
        plan.commit(agent_id, plan.to_positions(states))
    return failures
