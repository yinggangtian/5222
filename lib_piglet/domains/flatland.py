# domains/flatland.py
#
# The Flatland railway as a Piglet search domain.
#
# Piglet's gridmap domain will not do here. Its state is a bare (x, y) pair,
# but a train's legal moves depend on the direction it is already facing: the
# same cell offers different exits to a train arriving from the north and one
# arriving from the west. Search a Flatland map as a plain grid and the paths
# that come out are ones the simulator rejects.
#
# A state is therefore a cell paired with a heading, packed into one integer:
#
#     state = (row * width + column) * 4 + heading
#
# Questions 2 and 3 add a time dimension, and pack that on top:
#
#     timed state = timestep * n_states + state
#
# Both encodings keep a state a plain int, which is what makes Piglet's
# search_node hashing cheap enough for the millions of nodes a whole
# assessment run generates.
#
# @author: Yinggang Tian
#

from array import array
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from lib_piglet.domains.base_domain import base_domain

#: Flatland's heading encoding.
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3

#: Row/column offset produced by moving one cell in each heading.
DELTA: Tuple[Tuple[int, int], ...] = ((-1, 0), (0, 1), (1, 0), (0, -1))

#: Distance recorded for states from which the goal cannot be reached at all.
UNREACHABLE = 1 << 30

#: A state is an int; see the module docstring for the encoding.
flatland_state = int


class flatland_domain(base_domain[int]):
    """One Flatland rail map, as a directed graph over (cell, heading).

    Built once per map and shared by every agent planned on it: the transition
    tables and the goal distance tables are the expensive part, and neither
    depends on which train is being planned.
    """

    def get_name(self):
        return "flatland"

    def __init__(self, rail):
        """Decode a Flatland ``GridTransitionMap`` into successor tables.

        Only ``grid``, ``width`` and ``height`` are read, so a bare object
        exposing those also works -- which keeps the domain testable without
        starting the simulator.
        """
        self.width_: int = int(rail.width)
        self.height_: int = int(rail.height)
        self.n_cells_: int = self.width_ * self.height_
        self.n_states_: int = self.n_cells_ * 4

        edge_from, edge_to = self._extract_edges(np.asarray(rail.grid))
        succ_mat = self._adjacency_matrix(edge_from, edge_to)
        self._pred_mat = self._adjacency_matrix(edge_to, edge_from)

        # Expanders iterate successors far more often than anything else, so
        # pay once for a list of plain tuples rather than slicing numpy rows in
        # the inner loop.
        self.succ_: List[Tuple[int, ...]] = [
            tuple(int(v) for v in row if v >= 0) for row in succ_mat
        ]

        self._distances: Dict[int, array] = {}
        self._last_goal_cell: int = -1
        self._last_distances: Optional[array] = None

    # ------------------------------------------------------------------
    # the domain interface Piglet's searches call
    # ------------------------------------------------------------------

    def is_goal(self, current_state: int, goal_state: int) -> bool:
        """Has the train arrived?

        Arrival is about the cell, not the heading: a train has reached its
        station whichever way it is facing. The modulo strips the timestep, so
        the same test serves the plain search of question 1 and the space-time
        searches of questions 2 and 3.
        """
        n = self.n_states_
        return (current_state % n) >> 2 == (goal_state % n) >> 2

    # ------------------------------------------------------------------
    # state encoding
    # ------------------------------------------------------------------
#question1.py
    def state_of(self, position: Sequence[int], direction: int) -> int:
        """Encode a ``(row, column)`` position and heading as a state."""
        return (int(position[0]) * self.width_ + int(position[1])) * 4 + int(direction)

    def position_of(self, state: int) -> Tuple[int, int]:
        """The ``(row, column)`` position a state sits in."""
        cell = (state % self.n_states_) >> 2
        return (cell // self.width_, cell % self.width_)

    def cell_index(self, position: Sequence[int]) -> int:
        """Flat cell index (``row * width + column``) of a position."""
        return int(position[0]) * self.width_ + int(position[1])

    def goal_state(self, goal: Sequence[int]) -> int:
        """A canonical state standing on ``goal``, for the searches' goal test."""
        return self.cell_index(goal) * 4

    def at_time(self, state: int, timestep: int) -> int:
        """Pack a rail state and a timestep into one space-time state."""
        return timestep * self.n_states_ + state

    def split_time(self, timed_state: int) -> Tuple[int, int]:
        """Unpack a space-time state into ``(timestep, rail state)``."""
        return divmod(timed_state, self.n_states_)

    def successors(self, state: int) -> Tuple[int, ...]:
        """Rail states reachable in one move from a rail state."""
        return self.succ_[state]

    # ------------------------------------------------------------------
    # goal distances
    # ------------------------------------------------------------------
# reverse BFS for Question 1
    def goal_distances(self, goal_state: int) -> array:
        """Exact remaining cost of every state, for one goal.

        Manhattan distance is admissible on a Flatland map but very weak: the
        rails wind, junctions are one-way, and a train facing the wrong way may
        have to run to the next dead end before it can turn around. A search
        guided by it wanders.

        Every move costs one timestep, so a backward breadth-first search from
        the goal gives the *exact* remaining cost of every state at once --
        the strongest admissible heuristic there is, and one that makes A*
        expand only states on an optimal path. It is computed once per goal and
        reused by every query against it, which is what makes it affordable
        when a level 6 instance has 150 goals over 90,000 states.
        """
        goal_cell = (goal_state % self.n_states_) >> 2
        if goal_cell == self._last_goal_cell:
            return self._last_distances
        table = self._distances.get(goal_cell)
        if table is None:
            table = self._backward_bfs(goal_cell)
            self._distances[goal_cell] = table
        self._last_goal_cell = goal_cell
        self._last_distances = table
        return table

    def shortest_path(
        self, state: int, goal_state: int, limit: Optional[int] = None
    ) -> Optional[List[int]]:
        """Walk the distance table downhill, as a list of rail states.

        Following the exact distances downhill is a shortest path by
        construction, so this replaces a search whenever nothing else
        constrains the train.

        Returns ``None`` if the goal is unreachable, or further away than
        ``limit`` moves.
        """
        dist = self.goal_distances(goal_state)
        state = state % self.n_states_
        remaining = dist[state]
        if remaining >= UNREACHABLE:
            return None
        if limit is not None and remaining > limit:
            return None

        states = [state]
        while remaining:
            remaining -= 1
            for nxt in self.succ_[state]:
                if dist[nxt] == remaining:
                    state = nxt
                    break
            else:  # pragma: no cover -- the distance table rules this out
                return None
            states.append(state)
        return states

    def _backward_bfs(self, goal_cell: int) -> array:
        """Level-synchronous BFS from the goal, following edges backwards.

        Whole frontiers are expanded with numpy indexing rather than a Python
        loop over each state: on a 150x150 map that is 90,000 states per goal
        and 150 goals per instance, which is far too much to walk a node at a
        time. The result is handed back as an ``array('i')`` because indexing
        one yields a plain Python int, where a numpy array would hand the
        search a numpy scalar to do all its arithmetic on.
        """
        pred = self._pred_mat
        dist = np.full(self.n_states_, UNREACHABLE, dtype=np.int32)

        base = goal_cell * 4
        frontier = np.array([base, base + 1, base + 2, base + 3], dtype=np.int64)
        dist[frontier] = 0

        depth = 0
        while frontier.size:
            depth += 1
            candidates = pred[frontier].ravel()
            candidates = candidates[candidates >= 0]
            candidates = candidates[dist[candidates] == UNREACHABLE]
            if candidates.size == 0:
                break
            frontier = np.unique(candidates)
            dist[frontier] = depth
        return array("i", dist.tolist())

    # ------------------------------------------------------------------
    # construction
    # ------------------------------------------------------------------

    def _extract_edges(self, grid: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Every legal ``(cell, heading) -> (cell, heading)`` move on the map.

        Flatland packs a cell's transitions into 16 bits: one nibble per
        heading the train may arrive with, and within that nibble one bit per
        heading it may leave with, ordered N, E, S, W from the most significant
        bit. Peeling that apart one heading pair at a time turns each of the
        sixteen combinations into a whole-grid boolean mask, so the tables are
        built with numpy rather than a Python loop over every cell.
        """
        height, width = self.height_, self.width_
        rows = np.arange(height, dtype=np.int64)[:, None]
        cols = np.arange(width, dtype=np.int64)[None, :]
        cell_ids = rows * width + cols

        froms: List[np.ndarray] = []
        tos: List[np.ndarray] = []
        for facing in range(4):
            nibble = (grid >> ((3 - facing) * 4)) & 0xF
            for exit_dir in range(4):
                allowed = ((nibble >> (3 - exit_dir)) & 1).astype(bool)
                if not allowed.any():
                    continue
                d_row, d_col = DELTA[exit_dir]
                # A transition never points off the map on a well formed
                # Flatland instance; the bounds mask keeps a malformed one from
                # wrapping around the flat index.
                in_bounds = np.zeros_like(allowed)
                r_lo, r_hi = max(0, -d_row), min(height, height - d_row)
                c_lo, c_hi = max(0, -d_col), min(width, width - d_col)
                in_bounds[r_lo:r_hi, c_lo:c_hi] = True
                mask = allowed & in_bounds
                if not mask.any():
                    continue
                source = cell_ids[mask]
                froms.append(source * 4 + facing)
                tos.append((source + d_row * width + d_col) * 4 + exit_dir)

        if not froms:
            empty = np.zeros(0, dtype=np.int64)
            return empty, empty
        return np.concatenate(froms), np.concatenate(tos)

    def _adjacency_matrix(self, keys: np.ndarray, values: np.ndarray) -> np.ndarray:
        """Group ``values`` by ``keys`` into a padded ``(n_states, 4)`` table."""
        table = np.full((self.n_states_, 4), -1, dtype=np.int32)
        if keys.size == 0:
            return table
        order = np.argsort(keys, kind="stable")
        keys, values = keys[order], values[order]
        # Position of each entry within its own key's run, so entries land in
        # consecutive columns of that key's row.
        slot = np.arange(keys.size) - np.searchsorted(keys, keys, side="left")
        table[keys, slot] = values
        return table
