"""Trip orchestration: tie geocoding + routing + the HOS engine together,
then slice the resulting event list into per-calendar-day log data.

This is the one place that knows about all three pieces. The DRF view (B3)
calls `plan` and serializes the result.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..hos import DutyStatus, plan_trip
from .geocoding import Place, geocode
from .routing import Coord, RouteLeg, route

# A driver's paper log day runs midnight to midnight.
MINUTES_PER_DAY = 24 * 60


@dataclass
class DayLog:
    """One calendar day's worth of log-sheet data."""

    date: str                       # "YYYY-MM-DD"
    segments: list[dict]            # {duty_status, start_min, end_min, label} in min-of-day
    totals: dict                    # minutes per duty status (should sum to <=1440)


@dataclass
class TripResult:
    current: Place
    pickup: Place
    dropoff: Place
    leg1: RouteLeg
    leg2: RouteLeg
    plan: object                    # hos.TripPlan
    days: list[DayLog]
    start_datetime: datetime


def _slice_into_days(plan, start_dt: datetime) -> list[DayLog]:
    """Split the engine's minute-based events into midnight-bounded day logs.

    An event that crosses midnight is clipped into a piece on each day. Times
    within a day are expressed as minutes since that day's midnight (0..1440).
    """
    # Bucket of clipped segments per date.
    buckets: dict[str, list[dict]] = defaultdict(list)

    for ev in plan.events:
        ev_start = start_dt + timedelta(minutes=ev.start_min)
        ev_end = start_dt + timedelta(minutes=ev.end_min)

        # Walk day-by-day, clipping the event to each day's midnight boundaries.
        cursor = ev_start
        while cursor < ev_end:
            day_midnight = cursor.replace(hour=0, minute=0, second=0, microsecond=0)
            next_midnight = day_midnight + timedelta(days=1)
            piece_end = min(ev_end, next_midnight)

            start_of_day_min = (cursor - day_midnight).total_seconds() / 60.0
            end_of_day_min = (piece_end - day_midnight).total_seconds() / 60.0

            buckets[day_midnight.strftime("%Y-%m-%d")].append({
                "duty_status": ev.duty_status.value,
                "start_min": round(start_of_day_min, 3),
                "end_min": round(end_of_day_min, 3),
                "label": ev.label,
            })
            cursor = piece_end

    days: list[DayLog] = []
    for date in sorted(buckets):
        segments = buckets[date]
        totals: dict[str, float] = {s.value: 0.0 for s in DutyStatus}
        for seg in segments:
            totals[seg["duty_status"]] += seg["end_min"] - seg["start_min"]
        totals = {k: round(v, 3) for k, v in totals.items()}
        days.append(DayLog(date=date, segments=segments, totals=totals))
    return days


def plan(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
    current_cycle_used: float,
    *,
    start_datetime: datetime | None = None,
) -> TripResult:
    """Run the full pipeline and return everything the frontend needs.

    Raises GeocodingError / RoutingError on external-service failure; the engine
    raises ValueError on impossible inputs.
    """
    start_dt = start_datetime or datetime.now(timezone.utc)
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    # 1) Geocode the three location strings.
    current = geocode(current_location)
    pickup = geocode(pickup_location)
    dropoff = geocode(dropoff_location)

    # 2) Route the two legs: current -> pickup, pickup -> dropoff.
    leg1 = route(Coord(current.lat, current.lon), Coord(pickup.lat, pickup.lon))
    leg2 = route(Coord(pickup.lat, pickup.lon), Coord(dropoff.lat, dropoff.lon))

    # 3) Simulate the HOS-constrained trip from the two leg distances.
    trip_plan = plan_trip(leg1.distance_miles, leg2.distance_miles, current_cycle_used)

    # 4) Slice the event timeline into per-day log sheets.
    days = _slice_into_days(trip_plan, start_dt)

    return TripResult(
        current=current,
        pickup=pickup,
        dropoff=dropoff,
        leg1=leg1,
        leg2=leg2,
        plan=trip_plan,
        days=days,
        start_datetime=start_dt,
    )
