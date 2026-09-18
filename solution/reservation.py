"""Space-time occupancy of the paths that are already committed.

Two trains collide in Flatland when they want the same cell at the same
timestep, or when they try to exchange cells.  Everything else is legal: the
simulator resolves a whole chain of trains moving up one cell together, so a
train may enter a cell in the very timestep its neighbour leaves it.  The
reservation table records exactly those two prohibitions and nothing more,
because being stricter than the simulator costs throughput on the congested
levels.

Reservations are keyed by timestep first.  A search expanding a node at time
``t`` does one dictionary lookup to get everything reserved at ``t + 1`` and
then only cheap integer lookups per successor, which keeps the inner loop of
:mod:`solution.space_time_astar` short.
"""

from typing import Dict, Optional, Sequence


class ReservationTable:
    """Cells and swaps claimed by already planned agents, indexed by timestep.

    Cells are flat indices (``row * width + column``) so that a whole move can
    be identified by one integer, ``origin * n_cells + destination``.
    """

    __slots__ = ("n_cells", "vertex", "swap", "horizon")

    def __init__(self, n_cells: int):
        self.n_cells = n_cells
        #: timestep -> cell -> agent standing there
        self.vertex: Dict[int, Dict[int, int]] = {}
        #: timestep -> packed move -> agent whose opposite move forbids it
        self.swap: Dict[int, Dict[int, int]] = {}
        #: last timestep carrying any reservation; -1 when the table is empty
        self.horizon = -1

    # ------------------------------------------------------------------
    # building
    # ------------------------------------------------------------------

    def add_path(self, agent_id: int, cells: Sequence[int], start_time: int = 0) -> None:
        """Claim every cell ``cells`` occupies, from ``start_time`` onwards.

        ``cells[i]`` is where the agent stands at timestep ``start_time + i``.
        A path ends when its agent reaches its target, at which point the
        simulator lifts it off the map, so nothing is reserved beyond the last
        entry.
        """
        if not cells:
            return
        n_cells = self.n_cells
        vertex, swap = self.vertex, self.swap
        previous = cells[0]
        time = start_time
        vertex.setdefault(time, {})[previous] = agent_id
        for cell in cells[1:]:
            time += 1
            vertex.setdefault(time, {})[cell] = agent_id
            if cell != previous:
                # This agent moves previous -> cell arriving at `time`, so the
                # opposite move arriving at the same timestep would be a swap.
                swap.setdefault(time, {})[cell * n_cells + previous] = agent_id
            previous = cell
        if time > self.horizon:
            self.horizon = time

    def remove_path(self, agent_id: int, cells: Sequence[int], start_time: int = 0) -> None:
        """Undo :meth:`add_path` for one agent, so it can be replanned."""
        if not cells:
            return
        n_cells = self.n_cells
        vertex, swap = self.vertex, self.swap
        previous = cells[0]
        time = start_time
        self._discard(vertex, time, previous, agent_id)
        for cell in cells[1:]:
            time += 1
            self._discard(vertex, time, cell, agent_id)
            if cell != previous:
                self._discard(swap, time, cell * n_cells + previous, agent_id)
            previous = cell

    @staticmethod
    def _discard(index: Dict[int, Dict[int, int]], time: int, key: int, agent_id: int) -> None:
        slot = index.get(time)
        if slot is not None and slot.get(key) == agent_id:
            del slot[key]
            if not slot:
                del index[time]

    # ------------------------------------------------------------------
    # queries
    # ------------------------------------------------------------------

    def occupant(self, cell: int, time: int) -> Optional[int]:
        """Which agent is standing on ``cell`` at ``time``, if any."""
        slot = self.vertex.get(time)
        return None if slot is None else slot.get(cell)

    def swap_partner(self, origin: int, destination: int, time: int) -> Optional[int]:
        """Which agent's move makes ``origin -> destination`` a swap at ``time``."""
        slot = self.swap.get(time)
        if slot is None:
            return None
        return slot.get(origin * self.n_cells + destination)
