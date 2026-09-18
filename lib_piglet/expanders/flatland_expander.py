# expanders/flatland_expander.py
#
# Expand functions for the Flatland domain.
#
# Two of them. flatland_expander searches (cell, heading), which is all
# question 1 needs: one train, no other traffic, no time dimension.
# flatland_time_expander adds the timestep and refuses the moves a
# reservation table forbids, which is what questions 2 and 3 run on.
#
# Following Piglet's grid_expander, everything a single query needs -- the
# reservations to respect, the goal, the arrival deadline -- is held on the
# expander, so one expander is built per query and the domain underneath is
# shared by every train on the map.
#
# @author: Yinggang Tian
#

from typing import List, Optional, Tuple

from lib_piglet.domains.flatland import UNREACHABLE, flatland_domain
from lib_piglet.domains.grid_action import Move_Actions, grid_action
from lib_piglet.expanders.base_expander import base_expander

#: Every action in Flatland takes exactly one timestep, and nothing about an
#: action varies between uses, so five shared instances stand in for the
#: millions of actions an assessment run would otherwise allocate.
_HEADING_MOVES = (
    Move_Actions.MOVE_UP,     # NORTH
    Move_Actions.MOVE_RIGHT,  # EAST
    Move_Actions.MOVE_DOWN,   # SOUTH
    Move_Actions.MOVE_LEFT,   # WEST
)


def _action(move: Move_Actions) -> grid_action:
    action = grid_action()
    action.move_ = move
    action.cost_ = 1
    return action


MOVES: Tuple[grid_action, ...] = tuple(_action(m) for m in _HEADING_MOVES)
WAIT: grid_action = _action(Move_Actions.MOVE_WAIT)


class flatland_expander(base_expander):
    """Successors of a ``(cell, heading)`` state -- question 1.

    States whose goal is unreachable are dropped rather than generated: the
    heuristic would price them out of ever being expanded anyway, and not
    generating them keeps them off the open list.
    """

    def __init__(self, domain: flatland_domain, goal_state: int):
        self.domain_: flatland_domain = domain
        self.goal_state_: int = goal_state
        self.distances_ = domain.goal_distances(goal_state)

    def expand(self, current) -> List[Tuple[int, grid_action]]:
        distances = self.distances_
        successors = []
        for nxt in self.domain_.succ_[current.state_]:
            if distances[nxt] < UNREACHABLE:
                successors.append((nxt, MOVES[nxt & 3]))
        return successors

    def __str__(self):
        return "flatland_expander"


class flatland_time_expander(base_expander):
    """Successors in space and time -- questions 2 and 3.

    Waiting becomes a real action here, because where a train may stand now
    depends on where the others will be. Two prohibitions are enforced, and
    only two: no two trains in one cell at one timestep, and no two trains
    exchanging cells. Everything else the simulator permits -- notably a whole
    chain of trains moving up one cell together, so a train may enter a cell in
    the very timestep its neighbour leaves it -- and being stricter than the
    simulator only costs throughput on the congested levels.

    Parameters
    ----------
    table:
        Reservations to respect. ``None`` means an empty railway.
    latest_arrival:
        Refuse to generate a state that can no longer reach the goal by this
        timestep.
    horizon:
        Stop honouring reservations after this timestep. Past the last
        reservation nothing can get in the train's way, so the expander stops
        branching and offers only the move that walks the exact distance table
        downhill: still optimal, and it turns the tail of a long journey from a
        search into a walk. Setting it deliberately short gives a plan that is
        safe for a while and optimistic after -- question 3 tried that as a way
        out for a boxed-in train and had to withdraw it, because two optimistic
        plans meeting head-on on single track can never be undone.
    budget:
        Give up after this many expansions by returning no successors, which
        drains the open list and lets the search report failure. A cap on the
        search rather than on the clock keeps runs reproducible.
    """

    def __init__(
        self,
        domain: flatland_domain,
        goal_state: int,
        table=None,
        latest_arrival: Optional[int] = None,
        horizon: Optional[int] = None,
        banned=None,
        budget: int = 200_000,
    ):
        self.domain_: flatland_domain = domain
        self.goal_state_: int = goal_state
        self.distances_ = domain.goal_distances(goal_state)
        self.reservation_table_ = table
        self.banned_ = banned or None
        self.latest_arrival_: Optional[int] = latest_arrival
        self.budget_: int = budget
        self.expansions_: int = 0

        table_horizon = -1 if table is None else table.horizon
        self.last_constrained_: int = (
            table_horizon if horizon is None else min(table_horizon, horizon)
        )

    def expand(self, current) -> List[Tuple[int, grid_action]]:
        self.expansions_ += 1
        if self.expansions_ > self.budget_:
            return []

        domain = self.domain_
        n_states = domain.n_states_
        time, state = divmod(current.state_, n_states)
        distances = self.distances_
        next_time = time + 1
        deadline = self.latest_arrival_

        if time >= self.last_constrained_:
            # Nothing is reserved from here on, so the rest of the journey is a
            # plain shortest path: offer only the one move that shortens it.
            remaining = distances[state] - 1
            if deadline is not None and time + distances[state] > deadline:
                return []
            banned = self.banned_
            for nxt in domain.succ_[state]:
                if distances[nxt] == remaining and not (banned and nxt in banned):
                    return [(next_time * n_states + nxt, MOVES[nxt & 3])]
            return []

        table = self.reservation_table_
        occupied = table.vertex.get(next_time)
        swapped = table.swap.get(next_time)
        cell = state >> 2
        successors = []

        # Waiting is available unless somebody has claimed this cell for the
        # next timestep.
        if occupied is None or cell not in occupied:
            if deadline is None or next_time + distances[state] <= deadline:
                successors.append((next_time * n_states + state, WAIT))

        n_cells = domain.n_cells_
        banned = self.banned_
        for nxt in domain.succ_[state]:
            remaining = distances[nxt]
            if remaining >= UNREACHABLE:
                continue
            if banned is not None and nxt in banned:
                continue
            if deadline is not None and next_time + remaining > deadline:
                continue
            target = nxt >> 2
            if occupied is not None and target in occupied:
                continue
            if swapped is not None and (cell * n_cells + target) in swapped:
                continue
            successors.append((next_time * n_states + nxt, MOVES[nxt & 3]))
        return successors

    def __str__(self):
        return "flatland_time_expander"
