"""HOS trip simulation engine.

The engine "drives" an imaginary trip minute by minute, applying the federal
Hours-of-Service (HOS) rules for a property-carrying driver on the 70hr/8day
cycle, and emits an ordered list of timed duty events. The map and log sheets
downstream only *display* this list.

INPUTS
    leg1_miles        miles from current location -> pickup
    leg2_miles        miles from pickup -> dropoff
    cycle_used_hours  on-duty hours already used in the rolling 8-day window
                      (the starting balance of the 70-hour clock)

OUTPUT
    TripPlan(events, summary)
      events  ordered list of Event, each with start/end minutes (from t=0),
              a human label, and the cumulative trip miles at that point.

All times are minutes measured from the trip's start (t = 0). Mapping those
minutes onto real calendar days/clock-times happens later (milestone B3); the
engine itself stays date-free so it is trivial to unit-test.

--- HOS rules applied ---
  * 11-hour driving limit per shift.
  * 14-hour driving window per shift (on-duty clock; breaks do NOT pause it).
  * 30-minute break required once 8 cumulative driving hours are reached.
  * 70-hour / 8-day on-duty cycle (driving + on-duty-not-driving count).
  * 10 consecutive hours off restarts the 11h & 14h clocks (daily reset).
  * 34 consecutive hours off restarts the 70-hour cycle.

--- Assumptions (NOT given in the spec; chosen here, flagged for review) ---
  * Average truck speed 55 mph (CLAUDE.md default).
  * Fuel stop once every 1,000 miles, 30 min on-duty each.
  * Pickup = 1h on-duty, Dropoff = 1h on-duty (CLAUDE.md).
  * The 30-min break = "30 consecutive minutes not driving", so ANY non-driving
    event of >= 30 min (pickup, dropoff, fuel, rest) also satisfies it. This
    matches the modern rule and avoids inserting redundant breaks.
  * 10-hr daily reset is logged as Sleeper berth; 30-min break and 34-hr
    restart are logged as Off Duty.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

# --- Rule constants (minutes unless noted) ------------------------------------

AVG_SPEED_MPH = 55.0

MAX_DRIVING = 11 * 60          # 11h driving per shift
MAX_WINDOW = 14 * 60          # 14h on-duty window per shift
BREAK_AFTER_DRIVING = 8 * 60   # 30-min break required after 8h cumulative driving
BREAK_DURATION = 30
DAILY_RESET = 10 * 60          # 10h off restarts shift clocks
CYCLE_LIMIT = 70 * 60          # 70h on-duty per rolling 8 days
CYCLE_RESET = 34 * 60          # 34h off restarts the cycle

FUEL_INTERVAL_MILES = 1000.0
FUEL_DURATION = 30
PICKUP_DURATION = 60
DROPOFF_DURATION = 60

# Float guard so we don't loop forever on rounding dust.
_EPS = 1e-6


class DutyStatus(str, Enum):
    """The four duty statuses, matching the four log-sheet rows."""

    DRIVING = "Driving"
    ON_DUTY = "OnDuty"      # on-duty, not driving (pickup, dropoff, fuel)
    OFF_DUTY = "OffDuty"     # 30-min break, 34-hr restart
    SLEEPER = "Sleeper"     # 10-hr daily rest


@dataclass
class Event:
    """One contiguous stretch of a single duty status."""

    duty_status: DutyStatus
    start_min: float       # minutes from trip start
    end_min: float
    label: str             # human remark, e.g. "Pickup", "30-min break"
    miles_marker: float    # cumulative trip miles where this event begins

    @property
    def duration_min(self) -> float:
        return self.end_min - self.start_min

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duty_status"] = self.duty_status.value
        d["duration_min"] = self.duration_min
        return d


@dataclass
class TripPlan:
    events: list[Event] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "summary": self.summary,
        }


class _Sim:
    """Mutable simulation state. One instance == one planned trip."""

    def __init__(self, cycle_used_hours: float, avg_speed: float):
        self.speed = avg_speed
        self.now = 0.0               # minutes from trip start
        self.miles = 0.0             # cumulative miles driven

        # Shift clocks (reset by a 10h+ rest).
        self.shift_driving = 0.0     # driving minutes this shift
        self.window_start = 0.0      # when the current 14h window opened
        self.driving_since_break = 0.0

        # Cycle clock (reset by a 34h rest).
        self.cycle_used = cycle_used_hours * 60.0

        # Fuel tracking.
        self.miles_to_fuel = FUEL_INTERVAL_MILES

        self.events: list[Event] = []

    # --- low-level event emitters --------------------------------------------

    def _add(self, status: DutyStatus, duration: float, label: str) -> None:
        self.events.append(
            Event(
                duty_status=status,
                start_min=self.now,
                end_min=self.now + duration,
                label=label,
                miles_marker=self.miles,
            )
        )
        self.now += duration

    def _drive_chunk(self, minutes: float, label: str) -> None:
        miles = minutes / 60.0 * self.speed
        self._add(DutyStatus.DRIVING, minutes, label)
        self.miles += miles
        self.shift_driving += minutes
        self.driving_since_break += minutes
        self.cycle_used += minutes
        self.miles_to_fuel -= miles

    def _on_duty(self, minutes: float, label: str) -> None:
        self._add(DutyStatus.ON_DUTY, minutes, label)
        self.cycle_used += minutes           # on-duty counts toward 70h cycle
        if minutes >= BREAK_DURATION:        # >=30 min not driving satisfies the break
            self.driving_since_break = 0.0

    def _take_break(self) -> None:
        self._add(DutyStatus.OFF_DUTY, BREAK_DURATION, "30-min break")
        self.driving_since_break = 0.0       # off-duty does NOT count toward cycle

    def _daily_reset(self) -> None:
        self._add(DutyStatus.SLEEPER, DAILY_RESET, "10-hr rest")
        self.shift_driving = 0.0
        self.driving_since_break = 0.0
        self.window_start = self.now         # new 14h window opens now

    def _cycle_reset(self) -> None:
        self._add(DutyStatus.OFF_DUTY, CYCLE_RESET, "34-hr restart")
        self.cycle_used = 0.0
        self.shift_driving = 0.0
        self.driving_since_break = 0.0
        self.window_start = self.now

    def _take_fuel(self) -> None:
        self._on_duty(FUEL_DURATION, "Fuel stop")
        self.miles_to_fuel = FUEL_INTERVAL_MILES

    # --- public-ish step builders --------------------------------------------

    def on_duty_task(self, minutes: float, label: str) -> None:
        """Pickup / dropoff. On-duty, not driving."""
        self._on_duty(minutes, label)

    def drive(self, total_miles: float, label: str) -> None:
        """Drive `total_miles`, inserting breaks / rests / fuel as the rules demand."""
        remaining = float(total_miles)
        while remaining > _EPS:
            # 1) Out of driving time or window? Take the 10h daily reset.
            drive_room = MAX_DRIVING - self.shift_driving
            window_room = MAX_WINDOW - (self.now - self.window_start)
            if drive_room <= _EPS or window_room <= _EPS:
                self._daily_reset()
                continue

            # 2) Cycle (70h) exhausted? Take the 34h restart.
            cycle_room = CYCLE_LIMIT - self.cycle_used
            if cycle_room <= _EPS:
                self._cycle_reset()
                continue

            # 3) Hit 8h driving since last break? Take the 30-min break.
            break_room = BREAK_AFTER_DRIVING - self.driving_since_break
            if break_room <= _EPS:
                self._take_break()
                continue

            # 4) Drive up to the nearest binding limit, then loop to react to it.
            remaining_min = remaining / self.speed * 60.0
            fuel_room_min = self.miles_to_fuel / self.speed * 60.0
            chunk = min(
                drive_room, window_room, cycle_room,
                break_room, fuel_room_min, remaining_min,
            )
            self._drive_chunk(chunk, label)
            remaining -= chunk / 60.0 * self.speed

            # Reached a fuel point with driving still to do? Fuel up.
            if self.miles_to_fuel <= _EPS and remaining > _EPS:
                self._take_fuel()

    # --- result ---------------------------------------------------------------

    def result(self) -> TripPlan:
        totals: dict[str, float] = {s.value: 0.0 for s in DutyStatus}
        for e in self.events:
            totals[e.duty_status.value] += e.duration_min
        summary = {
            "total_minutes": round(self.now, 3),
            "total_miles": round(self.miles, 3),
            "driving_minutes": round(totals[DutyStatus.DRIVING.value], 3),
            "on_duty_minutes": round(totals[DutyStatus.ON_DUTY.value], 3),
            "off_duty_minutes": round(totals[DutyStatus.OFF_DUTY.value], 3),
            "sleeper_minutes": round(totals[DutyStatus.SLEEPER.value], 3),
            "cycle_used_end_minutes": round(self.cycle_used, 3),
        }
        return TripPlan(events=self.events, summary=summary)


def plan_trip(
    leg1_miles: float,
    leg2_miles: float,
    cycle_used_hours: float,
    *,
    avg_speed: float = AVG_SPEED_MPH,
) -> TripPlan:
    """Plan a full trip and return its ordered duty events + summary totals.

    Sequence: drive leg 1 (current -> pickup), 1h pickup, drive leg 2
    (pickup -> dropoff), 1h dropoff. Breaks, daily/cycle resets and fuel stops
    are inserted automatically wherever the HOS rules require them.
    """
    if leg1_miles < 0 or leg2_miles < 0:
        raise ValueError("Leg distances must be non-negative.")
    if not (0 <= cycle_used_hours <= 70):
        raise ValueError("cycle_used_hours must be between 0 and 70.")
    if avg_speed <= 0:
        raise ValueError("avg_speed must be positive.")

    sim = _Sim(cycle_used_hours, avg_speed)
    sim.drive(leg1_miles, "Driving")
    sim.on_duty_task(PICKUP_DURATION, "Pickup")
    sim.drive(leg2_miles, "Driving")
    sim.on_duty_task(DROPOFF_DURATION, "Dropoff")
    return sim.result()
