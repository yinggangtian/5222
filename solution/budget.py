"""Wall-clock budget, so no instance can ever run away with the whole question.

The contest server gives a question one time limit for all 56 instances
together, and scores everything that never got to run at the worst possible
cost.  A single instance that hangs therefore does not cost that instance, it
costs the question -- which is exactly what happened on a hidden level 2 case
that the local problem set has no equivalent of.

Bounding the *work* is not enough.  Every loop in the planner terminates, but a
repair may plan sixty trains, each through several fallback rungs, each a
search allowed a hundred thousand expansions; multiply that by an episode of
2400 timesteps and the bound is technically finite and practically forever.
Only a clock catches that.

So each instance is given a share of what is left, and the planner degrades
rather than overruns: the neighbourhood search is skipped, replanning stops
searching and parks the trains it was asked to fix, and the episode plays out
to a poor score instead of no score at all.
"""

import time
from typing import Optional
#goal
#: What planning is allowed overall, in seconds, well under the contest
#: server's one hour for the question. The margin covers the simulator's own
#: execution time, which is not planning and is not measured here: locally that
#: is about a third of the wall clock again on top of planning.
RUN_SECONDS = 2400.0

#: Instances in a question, per the assignment specification. Used only to
#: divide the remaining time; the floor keeps a late instance from being handed
#: the entire remainder if the server ever runs more than this.
EXPECTED_INSTANCES = 56
MIN_REMAINING = 8

#: No single instance gets more than this, however much is left over.
MAX_INSTANCE_SECONDS = 60.0


class _Clock:
    """The deadline the current instance is planning against."""

    def __init__(self):
        self.run_start: Optional[float] = None
        self.instances_done: int = 0
        self.deadline: float = 0.0

    def start_instance(self) -> float:
        """Open a fresh budget for one instance; returns its seconds."""
        now = time.monotonic()
        if self.run_start is None:
            self.run_start = now
        remaining_run = RUN_SECONDS - (now - self.run_start)
        remaining_instances = max(
            MIN_REMAINING, EXPECTED_INSTANCES - self.instances_done
        )
        seconds = max(1.0, min(MAX_INSTANCE_SECONDS, remaining_run / remaining_instances))
        self.instances_done += 1
        self.deadline = now + seconds
        return seconds

    def left(self) -> float:
        """Seconds still available to this instance; never negative."""
        if self.run_start is None:
            return MAX_INSTANCE_SECONDS
        return max(0.0, self.deadline - time.monotonic())

    def plan_left(self) -> float:
        """Seconds available to initial planning and LNS.

        Q3's planner and LNS share the same per-instance allowance in this
        version.  Keeping this named method makes the clock compatible with
        the deadline-aware fleet planner without changing the established
        runtime policy.
        """
        return self.left()

    def spent(self) -> bool:
        """True once this instance has used its share."""
        return self.left() <= 0.0


#: One clock per process, because the evaluator runs one instance at a time.
clock = _Clock()
