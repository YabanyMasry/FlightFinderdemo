"""FlightFinder: two-phase funnel for finding the globally cheapest flight.

Phase 1 (broad, cheap): bulk "explore" endpoints scan the whole
origin x destination x date space in few calls and rank rough candidates.

Phase 2 (narrow, expensive): real fare searches verify only the top candidates,
applying exact min/max stay constraints, and return the true cheapest itinerary.
"""

__version__ = "0.1.0"
