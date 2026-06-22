"""Trip orchestration: tie geocoding + routing + the HOS engine together,
then slice the resulting event list into per-calendar-day log data.

This is the one place that knows about all three pieces. The DRF view (B3)
calls `plan` and serializes the result.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ..hos import DutyStatus, plan_trip
from .geocoding import Place, geocode, reverse_geocode
from .routing import Coord, RouteLeg, route

# A driver's paper log day runs midnight to midnight.
MINUTES_PER_DAY = 24 * 60

# Engine tag -> real log activity term for the remarks.
ACTIVITY = {
    "Driving": "Driving",
    "Pickup": "Loading",
    "Dropoff": "Unloading",
    "Fuel stop": "Fueling",
    "30-min break": "30-min break",
    "10-hr rest": "10-hr break",
    "34-hr restart": "34-hr break",
}

_EARTH_RADIUS_MI = 3958.8


def _haversine_mi(a, b):
    lat1, lon1 = a
    lat2, lon2 = b
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    h = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * _EARTH_RADIUS_MI * math.asin(math.sqrt(h))


def _point_at_mileage(geometry, target_mi):
    """[lat, lon] on the route polyline at `target_mi` cumulative miles."""
    if not geometry:
        return None
    if target_mi <= 0:
        return geometry[0]
    acc = 0.0
    for i in range(1, len(geometry)):
        seg = _haversine_mi(geometry[i - 1], geometry[i])
        if acc + seg >= target_mi:
            frac = (target_mi - acc) / seg if seg else 0
            (lat1, lon1), (lat2, lon2) = geometry[i - 1], geometry[i]
            return [lat1 + (lat2 - lat1) * frac, lon1 + (lon2 - lon1) * frac]
        acc += seg
    return geometry[-1]


def _enrich_events(plan, current, pickup, dropoff, combined_geometry, leg1_miles):
    """Attach a 'City, ST' location + activity phrase to each engine event.

    Known endpoints (start, pickup, dropoff) reuse their forward-geocoded
    short names; mid-route stops are reverse-geocoded (cached by coordinate so
    each distinct stop costs at most one request).
    """
    cache: dict[tuple, str | None] = {}
    last_i = len(plan.events) - 1
    for i, ev in enumerate(plan.events):
        if i == 0 and ev.label == "Driving":
            ev.activity = "Pre-trip inspection"
        elif i == last_i and ev.label == "Dropoff":
            ev.activity = "Unloading, post-trip inspection"
        else:
            ev.activity = ACTIVITY.get(ev.label, ev.label)

        if ev.miles_marker <= 0.01:
            ev.location = current.short_name
        elif ev.label == "Pickup" or abs(ev.miles_marker - leg1_miles) < 0.5:
            ev.location = pickup.short_name
        elif ev.label == "Dropoff":
            ev.location = dropoff.short_name
        else:
            coord = _point_at_mileage(combined_geometry, ev.miles_marker)
            if coord is None:
                continue
            key = (round(coord[0], 3), round(coord[1], 3))
            if key not in cache:
                cache[key] = reverse_geocode(coord[0], coord[1])
            ev.location = cache[key]


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
        # Only the first piece carries the remark (the real status change);
        # a continuation after midnight is not a new change.
        cursor = ev_start
        first_piece = True
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
                "label": ev.label if first_piece else None,
                "location": ev.location if first_piece else None,
                "activity": ev.activity if first_piece else None,
            })
            cursor = piece_end
            first_piece = False

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
    # Anchor every trip to 06:00 on day 1 so the first sheet reads like a normal
    # working day (morning off-duty fill before the start) and short trips stay
    # on a single sheet. An explicit start_datetime still overrides this.
    start_dt = start_datetime or datetime.now(timezone.utc).replace(
        hour=6, minute=0, second=0, microsecond=0
    )
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

    # 4) Label each event with a "City, ST" + activity for the log remarks.
    _enrich_events(
        trip_plan, current, pickup, dropoff,
        leg1.geometry + leg2.geometry, leg1.distance_miles,
    )

    # 5) Slice the event timeline into per-day log sheets.
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
