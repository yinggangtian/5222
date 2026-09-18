from lib_piglet.utils.tools import eprint
from typing import List, Tuple
import glob, os, sys, time, json

from solution.budget import clock
from solution.context import domain_for
from solution.lns import improve
from solution.prioritized import FleetPlan, plan_fleet
from solution.replanner import repair
from solution.safeguard import never_crash

# import necessary modules that this python scripts need.
try:
    from flatland.core.transition_map import GridTransitionMap
    from flatland.envs.agent_utils import EnvAgent
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
# Reimplementing the content in get_path() function and replan() function.
#
# They both return a list of paths. A path is a list of (x,y) location tuples.
# The path should be conflict free.
# Hint, you could use some global variables to reuse many resources across get_path/replan frunction calls.
#########################


# This function return a list of location tuple as the solution.
# @param env The flatland railway environment
# @param agents A list of EnvAgent.
# @param max_timestep The max timestep of this episode.
# @return path A list of (x,y) tuple.
@never_crash(lambda agents, rail, max_timestep: [
    [agent.initial_position] * max_timestep for agent in agents
])
def get_path(agents: List[EnvAgent], rail: GridTransitionMap, max_timestep: int):
    ############
    # Prioritised planning: plan the trains one at a time, each treating the
    # plans already made as moving obstacles, using the same optimal
    # space-time A* as question 2.
    #
    # The order is by slack -- deadline minus shortest possible journey -- so
    # the trains that would be penalised for every timestep of delay get first
    # pick of the railway, and the ones with time to spare take the detours.
    #
    # The resulting plan is kept in a module-level FleetPlan so that replan()
    # can repair it in place rather than starting over.
    ############
    global _plan
    # Everything from here to the end of the episode -- this plan, and every
    # repair the episode triggers -- shares one wall-clock budget, so a hidden
    # instance that the planner handles badly cannot take the whole question
    # down with it.
    # start time write
    clock.start_instance()
    _plan = FleetPlan(domain_for(rail), agents, max_timestep)
    plan_fleet(_plan, agents)
    # Prioritised planning never revisits its own ordering, which is where most
    # of the remaining cost is. Spend the idle runtime budget tearing small
    # groups of trains out and putting them back in a different order.
    improve(_plan, agents, seconds=_lns_seconds(len(agents))) #LNS：large neighbourhood search
    return _plan.paths


#: Seconds of large neighbourhood search per instance, and per train within
#: it. The question's time budget covers all 56 instances together, so these
#: are sized to roughly double the planning time and no more, leaving the
#: contest server's single slower core a wide margin.
LNS_SECONDS = 4.0
LNS_PER_TRAIN = 0.03


MEDIUM_LNS_SECONDS = 12.0
MEDIUM_LNS_PER_TRAIN = 0.12


def _lns_seconds(n_agents: int) -> float:
    """LNS budget tuned by fleet size for Q3 robustness."""
    if 50 <= n_agents < 100:
        return min(MEDIUM_LNS_SECONDS, MEDIUM_LNS_PER_TRAIN * n_agents)
    return min(LNS_SECONDS, LNS_PER_TRAIN * n_agents)


#: The plan currently being executed. Rebuilt by get_path at the start of each
#: episode and repaired in place by replan.
_plan = None


# This function return a list of location tuple as the solution.
# @param rail The flatland railway GridTransitionMap
# @param agents A list of EnvAgent.
# @param current_timestep The timestep that malfunction/collision happens .
# @param existing_paths The existing paths from previous get_plan or replan.
# @param max_timestep The max timestep of this episode.
# @param new_malfunction_agents  The id of agents have new malfunction happened at current time step (Does not include agents already have malfunciton in past timesteps)
# @param failed_agents  The id of agents failed to reach the location on its path at current timestep.
# @return path_all  Return paths that locaitons from current_timestp is updated to handle malfunctions and failed execuations.
@never_crash(lambda agents, rail, current_timestep, existing_paths, *rest: existing_paths)
def replan(
    agents: List[EnvAgent],
    rail: GridTransitionMap,
    current_timestep: int,
    existing_paths: List[Tuple],
    max_timestep: int,
    new_malfunction_agents: List[int],
    failed_agents: List[int],
):
    ############
    # Local repair: replan the trains the breakdown actually invalidated --
    # the broken ones, the ones stuck behind them, and the ones whose path
    # runs through a cell a broken train is now sitting in -- and leave every
    # other train's path, and therefore its reservations, alone.
    #
    # Breakdowns are frequent and episodes are long, so replanning the whole
    # fleet here would spend the question's entire time budget on a handful of
    # instances. See solution/replanner.py for the two-phase repair.
    ############
    if _plan is None:  # pragma: no cover -- replan always follows get_path
        return existing_paths
    repair(_plan, agents, current_timestep, new_malfunction_agents, failed_agents)
    return _plan.paths


#####################################################################
# Instantiate a Remote Client
# You should not modify codes below, unless you want to modify test_cases to test specific instance.
#####################################################################
if __name__ == "__main__":
    if len(sys.argv) > 1:
        remote_evaluator(get_path, sys.argv, replan=replan)
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
        deadline_files = [test.replace(".pkl", ".ddl") for test in test_cases]
        evaluator(
            get_path,
            test_cases,
            debug=debug,
            visualizer=visualizer,
            question_type=3,
            ddl=deadline_files,
            replan=replan,
            max_steps=max_steps,
        )
