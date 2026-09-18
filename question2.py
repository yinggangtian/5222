"""
This is the python script for question 2. In this script, you are required to implement a multi agent path-finding algorithm
"""

from lib_piglet.utils.tools import eprint
import glob, os, sys

from solution.context import domain_for
from solution.reservation import ReservationTable
from solution.safeguard import never_crash
from solution.search import find_timed_path, states_to_path


# import necessary modules that this python scripts need.
try:
    from flatland.core.transition_map import GridTransitionMap
    from flatland.utils.controller import (
        get_action,
        Train_Actions,
        Directions,
        check_conflict,
        path_controller,
        evaluator,
        remote_evaluator,
        VisualiserOptions,
    )
except Exception as e:
    eprint("Cannot load flatland modules!", e)
    exit(1)

#########################
# Debugger and visualiser options
#########################

# Set debug to True for a step-by-step account of the run: what was planned,
# which agents malfunctioned or were blocked, and why each episode ended.
debug = False

# Controls the visualiser:
#   False                  -> run headless (fastest)
#   True                   -> watch the run with the default settings
#   VisualiserOptions(...) -> watch the run with your own settings, e.g.
#       VisualiserOptions(
#           delay=0.3,      # seconds to pause between timesteps; 0 runs at full speed
#           headless=False, # True: no window, serve to your browser instead
#           wait=True,      # hold the first frame until you are watching
#           port=8080,      # serve on a fixed port (headless mode)
#           cell_size=40,   # pixels per grid cell
#       )
visualizer = False

# Stop each episode after this many timesteps. None uses the test case's own
# limit.
max_steps = None

# If you want to test on specific instance, turn test_single_instance to True and specify the level and test number
test_single_instance = False
level = 0
test = 0

#########################
# Reimplementing the content in get_path() function.
#
# Return a list of (x,y) location tuples which connect the start and goal locations.
# The path should avoid conflicts with existing paths.
#########################


# This function return a list of location tuple as the solution.
# @param start A tuple of (x,y) coordinates
# @param start_direction An Int indicate direction.
# @param goal A tuple of (x,y) coordinates
# @param rail The flatland railway GridTransitionMap
# @param agent_id The id of given agent
# @param existing_paths A list of lists of locations indicate existing paths. The index of each location is the time that
# @param max_timestep The max timestep of this episode.
# @return path A list of (x,y) tuple.
@never_crash(lambda *args: [])
def get_path(
    start: tuple,
    start_direction: int,
    goal: tuple,
    rail: GridTransitionMap,
    agent_id: int,
    existing_paths: list,
    max_timestep: int,
):
    ############
    # Space-time A*: the question 1 search with a time dimension added.
    #
    # The trains already on the map are fixed obstacles that move, so the
    # reservation table records which cell each of them holds at each timestep
    # and which swaps that forbids. The search plans around them, waiting in
    # place whenever waiting is cheaper than going around.
    #
    # Costs are still uniform, so the exact goal distance stays a perfect
    # heuristic, and past the reservation horizon the plan is completed by
    # walking that distance table downhill instead of searching.
    ############
    domain = domain_for(rail)
    table = _reservations(domain, agent_id, existing_paths)

    start_state = domain.state_of(start, start_direction)

    # A train is put on its start cell the moment the episode begins, so a
    # train already scheduled to be there is a collision no plan can dodge.
    # The specification asks for an empty path in that case: the train then
    # never departs, which at least keeps it out of everybody else's way.
    if table.occupant(domain.cell_index(start), 0) is not None:
        return []

    states = find_timed_path(
        domain,
        start_state,
        domain.goal_state(goal),
        table,
        start_time=0,
        latest_arrival=max_timestep - 1,
    )
    if states is None:
        return []
    return states_to_path(domain, states)


#: Reservation table for the current instance, grown one path at a time.
# The evaluator calls get_path once per agent and passes back every path
# planned so far, so rebuilding the table each call would be quadratic in the
# number of agents. Instead the table is kept between calls and only the paths
# it has not seen yet are added.
_reservation_state: dict = {"domain": None, "table": None, "count": 0}


def _reservations(domain, agent_id: int, existing_paths: list) -> ReservationTable:
    """The reservation table describing ``existing_paths`` on ``domain``."""
    state = _reservation_state
    if agent_id == 0 or state["domain"] is not domain or state["table"] is None:
        state["domain"] = domain
        state["table"] = ReservationTable(domain.n_cells_)
        state["count"] = 0

    table = state["table"]
    width = domain.width_
    for other_id in range(state["count"], len(existing_paths)):
        path = existing_paths[other_id]
        table.add_path(other_id, [p[0] * width + p[1] for p in path])
    state["count"] = len(existing_paths)
    return table


#########################
# You should not modify codes below, unless you want to modify test_cases to test specific instance. You can read it know how we ran flatland environment.
########################
if __name__ == "__main__":
    if len(sys.argv) > 1:
        remote_evaluator(get_path, sys.argv)
    else:
        script_path = os.path.dirname(os.path.abspath(__file__))
        test_cases = glob.glob(
            os.path.join(script_path, "multi_test_case/level*_test_*.pkl")
        )
        if test_single_instance:
            test_cases = glob.glob(
                os.path.join(
                    script_path,
                    "multi_test_case/level{}_test_{}.pkl".format(level, test),
                )
            )
        test_cases.sort()
        evaluator(
            get_path,
            test_cases,
            debug=debug,
            visualizer=visualizer,
            question_type=2,
            max_steps=max_steps,
        )
