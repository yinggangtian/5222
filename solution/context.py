"""Per-map cache shared across the evaluator's many planner calls.

The evaluator hands the planner a fresh deep copy of the rail map on every
call: once per agent in question 2, once per replan in question 3.  Decoding
the transition tables and computing the goal distances each time would dominate
the runtime, and none of it depends on which agent is being planned.

``domain_for`` therefore keys a :class:`lib_piglet.domains.flatland` instance on
the contents of the grid and hands the same one back for every call about the
same map -- so the tables are built once and the distance table for each goal
is computed once.  Only the most recent map is kept: the distance tables are
the largest thing here, and once the evaluator has moved on to the next
instance the previous instance's tables are pure overhead.
"""

from typing import Optional

from lib_piglet.domains.flatland import flatland_domain

_cached_key: Optional[bytes] = None
_cached_domain: Optional[flatland_domain] = None


def domain_for(rail) -> flatland_domain:
    """The Flatland domain for ``rail``, reusing the last one when it matches."""
    global _cached_key, _cached_domain
    key = rail.grid.tobytes()
    if key != _cached_key or _cached_domain is None:
        _cached_domain = flatland_domain(rail)
        _cached_key = key
    return _cached_domain
