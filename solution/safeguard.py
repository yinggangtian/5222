"""Keep one bad instance from taking a whole question's marks down with it.

The contest server scores a question by running all 56 instances in a single
process.  An exception anywhere kills that process, and every instance that had
not run yet is scored at the worst possible cost -- so a bug that ought to cost
one instance costs the entire question instead.

Degrading to a safe plan instead keeps the rest of the run alive.  The
traceback still goes to stderr: swallowing a bug quietly is how it survives to
the next submission.
"""

import sys
import traceback
from functools import wraps


def never_crash(fallback):
    """Return a decorator that answers with ``fallback(*args)`` on any error.

    ``fallback`` is called with the same arguments the planner was, so it can
    build something shaped like a real answer -- an empty path, or a plan that
    parks every train where it stands.
    """

    def decorate(planner):
        @wraps(planner)
        def guarded(*args, **kwargs):
            try:
                return planner(*args, **kwargs)
            except Exception:
                traceback.print_exc(file=sys.stderr)
                return fallback(*args, **kwargs)

        return guarded

    return decorate
