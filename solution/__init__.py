"""Planning for the FIT5222 Flatland challenge.

The searches are Piglet's.  What Piglet did not have was a Flatland domain --
its ``gridmap`` state is a bare ``(x, y)`` pair, and a train's legal moves
depend on the direction it is already facing -- so one was added to the
library alongside the domains that ship with it:

``lib_piglet/domains/flatland.py``          the railway as a (cell, heading) graph
``lib_piglet/expanders/flatland_expander.py``  successors, with and without time
``lib_piglet/heuristics/flatland_h.py``     exact goal distances

This package is the part above the search: the assignment-specific planning
that decides *what* to search for.

``search``       assembles Piglet's ``graph_search`` for one query
``reservation``  space-time occupancy of already committed paths
``context``      per-map cache, so the tables are built once per instance
``prioritized``  prioritised planning for a whole fleet (question 3)
``replanner``    malfunction recovery on top of a committed plan (question 3)
``safeguard``    keeps one bad instance from costing a whole question
"""
