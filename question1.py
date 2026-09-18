"""
This is the python script for question 1. In this script, you are required to implement a single agent path-finding algorithm
"""

from lib_piglet.utils.tools import eprint
import glob, os, sys

from solution.context import domain_for
from solution.safeguard import never_crash
from solution.search import find_path, states_to_path

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
    eprint("Cannot load flatland modules!")
    eprint(e)
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
#########################


# This function return a list of location tuple as the solution.
# @param start A tuple of (x,y) coordinates
# @param start_direction An Int indicate direction.
# @param goal A tuple of (x,y) coordinates
# @param rail The flatland railway GridTransitionMap
# @param max_timestep The max timestep of this episode.
# @return path A list of (x,y) tuple.
@never_crash(lambda *args: [])
def get_path(
    start: tuple,
    start_direction: int,
    goal: tuple,
    rail: GridTransitionMap,
    max_timestep: int,
):
    ############
    # Piglet's graph_search over the Flatland domain added to the library in
    # lib_piglet/domains/flatland.py, guided by exact goal distances.
    #
    # A train's legal moves depend on the direction it faces, so the search
    # space is a cell paired with a heading rather than a plain grid cell --
    # which is why Piglet's own gridmap domain will not do. Backward BFS from
    # the goal over that graph gives the exact remaining cost of every state,
    # a perfect admissible heuristic, so A* expands only states on an optimal
    # path.
    ############
    domain = domain_for(rail)
    start_state = domain.state_of(start, start_direction)
    goal_state = domain.goal_state(goal)

    states = find_path(domain, start_state, goal_state)
    if states is None or len(states) > max_timestep:
        # No route on this railway, or none the train could finish in time. An
        # empty plan keeps it in the depot rather than sending it somewhere it
        # cannot come back from.
        return []
    return states_to_path(domain, states)


#########################
# You should not modify codes below, unless you want to modify test_cases to test specific instance. You can read it know how we ran flatland environment.
########################
if __name__ == "__main__":
    if len(sys.argv) > 1:
        remote_evaluator(get_path, sys.argv)
    else:
        script_path = os.path.dirname(os.path.abspath(__file__))
        test_cases = glob.glob(
            os.path.join(script_path, "single_test_case/level*_test_*.pkl")
        )
        if test_single_instance:
            test_cases = glob.glob(
                os.path.join(
                    script_path,
                    "single_test_case/level{}_test_{}.pkl".format(level, test),
                )
            )
        test_cases.sort()
        evaluator(
            get_path,
            test_cases,
            debug=debug,
            visualizer=visualizer,
            question_type=1,
            max_steps=max_steps,
        )
