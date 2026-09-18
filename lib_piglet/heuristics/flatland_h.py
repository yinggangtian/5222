# heuristics/flatland_h.py
#
# Heuristics for the Flatland domain.
#
# @author: Yinggang Tian
#

from lib_piglet.domains.flatland import UNREACHABLE, flatland_domain


def piglet_heuristic(domain: flatland_domain, current_state: int, goal_state: int):
    """Exact remaining cost from ``current_state`` -- the default heuristic.

    Not an estimate: the domain runs a backward breadth-first search from the
    goal, and unit move costs make BFS order cost order, so what comes back is
    the real distance. A* guided by it expands only states on an optimal path.

    Accepts plain ``(cell, heading)`` states and the space-time states of
    questions 2 and 3 alike; the timestep is stripped, because how long a train
    still has to travel does not depend on when it set off.
    """
    return domain.goal_distances(goal_state)[current_state % domain.n_states_]


def manhattan_heuristic(domain: flatland_domain, current_state: int, goal_state: int):
    """Straight-line grid distance, ignoring the rails entirely.

    Kept for comparison. It is admissible but weak: it cannot see that the
    track winds, that junctions are one-way, or that a train facing the wrong
    way may have to run to the next dead end before it can turn around. Search
    guided by it wanders over most of the map before finding the line.
    """
    width = domain.width_
    current_cell = (current_state % domain.n_states_) >> 2
    goal_cell = (goal_state % domain.n_states_) >> 2
    return abs(current_cell // width - goal_cell // width) + abs(
        current_cell % width - goal_cell % width
    )
