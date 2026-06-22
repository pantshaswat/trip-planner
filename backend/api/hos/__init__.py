"""Framework-free Hours-of-Service (HOS) trip simulation engine.

No Django imports here. Pure Python so it can be unit-tested with plain numbers.
"""

from .engine import (
    DutyStatus,
    Event,
    TripPlan,
    plan_trip,
)

__all__ = ["DutyStatus", "Event", "TripPlan", "plan_trip"]
