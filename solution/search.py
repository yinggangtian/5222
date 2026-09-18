"""Wiring Piglet's search engine to the Flatland domain.

The searches themselves are Piglet's: :class:`lib_piglet.search.graph_search`
drives the loop, :class:`lib_piglet.utils.data_structure.bin_heap` is the open
list ordered on ``f``, and the pieces that make it a *Flatland* search are the
domain, expander and heuristic added to the library under
``lib_piglet/domains/flatland.py``, ``lib_piglet/expanders/flatland_expander.py``
and ``lib_piglet/heuristics/flatland_h.py``.

What is left here is assembly: build the expander that describes one query,
hand it to ``graph_search``, and turn the solution it returns back into the
list of ``(x, y)`` cells the evaluator expects.
"""

from typing import List, Optional, Sequence, Tuple

from lib_piglet.domains.flatland import flatland_domain
from lib_piglet.expanders.flatland_expander import (
    flatland_expander,
    flatland_time_expander,
)
from lib_piglet.heuristics.flatland_h import piglet_heuristic
from lib_piglet.search.graph_search import graph_search
from lib_piglet.utils.data_structure import bin_heap

#: Expansions one space-time query may spend before it is abandoned. Capping
#: the search rather than the clock keeps a run reproducible; prioritised
#: planning always has a looser plan to fall back on.
DEFAULT_BUDGET = 200_000


def compare_node_f_state(a, b):
    """Order the open list on f, breaking every tie on the state id.

    Piglet's own ``compare_node_f`` breaks f ties on h and stops there, which
    leaves nodes of equal f and equal h in whatever order the heap happens to
    hold them.  Any of them is an optimal choice for the train being planned,
    so within one search it does not matter -- but prioritised planning turns
    one train's arbitrary choice among equal-cost routes into a different
    railway for every train planned after it, and question 3 then replans
    around that for 2400 timesteps.  Measured over the 56 instances, leaving
    the tie open costs 6 arrivals and 3.5% of the final SIC.

    The tie-break is free here because of how a space-time state is packed:
    ``timestep * n_states + rail state`` compares as ``(timestep, rail state)``
    lexicographically, so one integer comparison settles it.  That is also what
    keeps this comparator out of the library -- it is a total order only for
    states encoded the way :mod:`lib_piglet.domains.flatland` encodes them.
    """
    if a.f_ != b.f_:
        return a.f_ >= b.f_
    return a.state_ >= b.state_


def find_path(
    domain: flatland_domain, start_state: int, goal_state: int
) -> Optional[List[int]]:
    """Shortest route from ``start_state`` onto the goal cell -- question 1.

    Nothing shares the map in question 1: one train, no collisions, no time
    dimension. What is left is a shortest path problem on the ``(cell,
    heading)`` graph, which A* with the exact-distance heuristic solves
    optimally while expanding nothing off the optimal path.
    """
    search = graph_search(
        bin_heap(compare_node_f_state),
        flatland_expander(domain, goal_state),
        heuristic_function=piglet_heuristic,
    )
    solution = search.get_path(start_state, goal_state)
    if solution is None:
        return None
    return [node.state_ for node in solution.paths_]


def find_timed_path(
    domain: flatland_domain,
    start_state: int,
    goal_state: int,
    table,
    start_time: int = 0,
    hold: int = 0,
    latest_arrival: Optional[int] = None,
    horizon: Optional[int] = None,
    banned=None,
    budget: int = DEFAULT_BUDGET,
) -> Optional[List[int]]:
    """Cheapest conflict-free route, as rail states from ``start_time`` on.

    Element ``i`` of the result is where the train stands at timestep
    ``start_time + i``.

    ``hold`` is a malfunction the train is already serving: it cannot move for
    that many timesteps whatever anyone else has planned, so the wait is
    prefixed to the answer rather than searched for, and the search starts from
    where the train will be when it is repaired.

    Returns ``None`` when no conflict-free route exists within the bounds.
    """
    n_states = domain.n_states_
    prefix = [start_state] * hold
    origin_time = start_time + hold

    if domain.is_goal(start_state, goal_state):
        return prefix + [start_state]

    search = graph_search(
        bin_heap(compare_node_f_state),
        flatland_time_expander(
            domain,
            goal_state,
            table=table,
            latest_arrival=latest_arrival,
            horizon=horizon,
            banned=banned,
            budget=budget,
        ),
        heuristic_function=piglet_heuristic,
    )
    solution = search.get_path(domain.at_time(start_state, origin_time), goal_state)
    if solution is None:
        return None
    return prefix + [node.state_ % n_states for node in solution.paths_]


def states_to_path(
    domain: flatland_domain, states: Sequence[int]
) -> List[Tuple[int, int]]:
    """Turn a state sequence into the ``(x, y)`` list the simulator expects.

    The evaluator reads a path positionally: ``path[t]`` is where the train
    must stand at timestep ``t``. Repeating a cell is therefore how a plan says
    "wait here".
    """
    position_of = domain.position_of
    return [position_of(state) for state in states]
