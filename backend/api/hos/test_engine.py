"""Unit tests for the HOS engine. Plain numbers, no Django, no UI.

Run from the backend/ directory:
    uv run python -m unittest api.hos.test_engine
"""

import unittest

from .engine import (
    AVG_SPEED_MPH,
    BREAK_DURATION,
    CYCLE_RESET,
    DAILY_RESET,
    DROPOFF_DURATION,
    FUEL_DURATION,
    MAX_DRIVING,
    MAX_WINDOW,
    PICKUP_DURATION,
    DutyStatus,
    plan_trip,
)


def statuses(plan):
    return [e.duty_status for e in plan.events]


def labels(plan):
    return [e.label for e in plan.events]


def total_for(plan, status):
    return sum(e.duration_min for e in plan.events if e.duty_status == status)


class TimelineInvariants(unittest.TestCase):
    """Properties that must hold for every plan."""

    def _check_invariants(self, plan):
        # Events are contiguous: each starts exactly where the previous ended.
        for prev, nxt in zip(plan.events, plan.events[1:]):
            self.assertAlmostEqual(prev.end_min, nxt.start_min, places=6)
        # First event starts at t=0.
        if plan.events:
            self.assertAlmostEqual(plan.events[0].start_min, 0.0, places=6)
        # Status durations sum to the total trip length.
        summed = sum(e.duration_min for e in plan.events)
        self.assertAlmostEqual(summed, plan.summary["total_minutes"], places=3)
        # Driving minutes == miles / speed (engine must not trust any API duration).
        expected_drive = plan.summary["total_miles"] / AVG_SPEED_MPH * 60.0
        self.assertAlmostEqual(
            plan.summary["driving_minutes"], expected_drive, places=3
        )

    def test_invariants_across_many_trips(self):
        cases = [
            (0, 0, 0),
            (55, 55, 0),
            (495, 0, 0),
            (300, 200, 20),
            (1500, 0, 0),
            (700, 800, 40),
            (165, 0, 68),
        ]
        for c in cases:
            with self.subTest(case=c):
                self._check_invariants(plan_trip(*c))


class ShortTripNoLimits(unittest.TestCase):
    """A trip small enough that no break/rest/fuel is ever triggered."""

    def setUp(self):
        # 55 mi each leg = exactly 1h driving each.
        self.plan = plan_trip(55, 55, cycle_used_hours=0)

    def test_exact_sequence(self):
        self.assertEqual(
            statuses(self.plan),
            [
                DutyStatus.DRIVING,   # leg 1
                DutyStatus.ON_DUTY,   # pickup
                DutyStatus.DRIVING,   # leg 2
                DutyStatus.ON_DUTY,   # dropoff
            ],
        )
        self.assertEqual(labels(self.plan), ["Driving", "Pickup", "Driving", "Dropoff"])

    def test_durations(self):
        self.assertAlmostEqual(total_for(self.plan, DutyStatus.DRIVING), 120.0)
        self.assertAlmostEqual(total_for(self.plan, DutyStatus.ON_DUTY),
                               PICKUP_DURATION + DROPOFF_DURATION)
        self.assertAlmostEqual(self.plan.summary["total_minutes"], 240.0)

    def test_no_break_rest_or_fuel(self):
        labs = labels(self.plan)
        for unexpected in ("30-min break", "10-hr rest", "Fuel stop", "34-hr restart"):
            self.assertNotIn(unexpected, labs)


class ThirtyMinuteBreak(unittest.TestCase):
    """Driving past 8 cumulative hours must force a 30-min break."""

    def setUp(self):
        # 9h of driving on leg 1 (495 mi). leg 2 = 0.
        self.plan = plan_trip(9 * AVG_SPEED_MPH, 0, cycle_used_hours=0)

    def test_break_inserted_after_8h(self):
        breaks = [e for e in self.plan.events if e.label == "30-min break"]
        self.assertEqual(len(breaks), 1)
        b = breaks[0]
        self.assertEqual(b.duty_status, DutyStatus.OFF_DUTY)
        self.assertAlmostEqual(b.duration_min, BREAK_DURATION)
        # Break starts at the 8-hour driving mark.
        self.assertAlmostEqual(b.start_min, 8 * 60)

    def test_driving_split_8_then_1(self):
        drives = [e for e in self.plan.events if e.duty_status == DutyStatus.DRIVING]
        self.assertEqual(len(drives), 2)
        self.assertAlmostEqual(drives[0].duration_min, 8 * 60)
        self.assertAlmostEqual(drives[1].duration_min, 1 * 60)

    def test_no_daily_reset(self):
        # 9h driving < 11h and window < 14h, so no sleeper rest.
        self.assertNotIn(DutyStatus.SLEEPER, statuses(self.plan))


class ElevenAndFourteenHourLimits(unittest.TestCase):
    """A long single leg must be broken into multiple shifts by 10h rests."""

    def setUp(self):
        # 1500 mi ~= 27.3h of pure driving -> several shifts.
        self.plan = plan_trip(1500, 0, cycle_used_hours=0)

    def test_has_daily_rests(self):
        rests = [e for e in self.plan.events if e.label == "10-hr rest"]
        self.assertGreaterEqual(len(rests), 2)
        for r in rests:
            self.assertEqual(r.duty_status, DutyStatus.SLEEPER)
            self.assertAlmostEqual(r.duration_min, DAILY_RESET)

    def test_no_shift_exceeds_limits(self):
        # Walk the timeline shift-by-shift (a shift ends at each 10h sleeper rest).
        drive_in_shift = 0.0
        window_open = 0.0
        for e in self.plan.events:
            if e.duty_status == DutyStatus.SLEEPER:
                drive_in_shift = 0.0
                window_open = e.end_min
                continue
            if e.duty_status == DutyStatus.DRIVING:
                drive_in_shift += e.duration_min
                # No driving beyond 11h in a shift...
                self.assertLessEqual(drive_in_shift, MAX_DRIVING + 1e-6)
                # ...and no driving after the 14h window closes.
                self.assertLessEqual(e.end_min - window_open, MAX_WINDOW + 1e-6)

    def test_fuel_stops_present(self):
        fuels = [e for e in self.plan.events if e.label == "Fuel stop"]
        self.assertGreaterEqual(len(fuels), 1)
        for f in fuels:
            self.assertEqual(f.duty_status, DutyStatus.ON_DUTY)
            self.assertAlmostEqual(f.duration_min, FUEL_DURATION)


class SeventyHourCycleReset(unittest.TestCase):
    """Starting near the 70h cap must force a 34h restart mid-trip."""

    def setUp(self):
        # Start with 68h used; 3h of driving pushes past 70h.
        self.plan = plan_trip(3 * AVG_SPEED_MPH, 0, cycle_used_hours=68)

    def test_cycle_restart_inserted(self):
        restarts = [e for e in self.plan.events if e.label == "34-hr restart"]
        self.assertEqual(len(restarts), 1)
        r = restarts[0]
        self.assertEqual(r.duty_status, DutyStatus.OFF_DUTY)
        self.assertAlmostEqual(r.duration_min, CYCLE_RESET)

    def test_restart_after_2h_driving(self):
        # 68h + 2h driving = 70h -> restart fires before the 3rd hour.
        restart = next(e for e in self.plan.events if e.label == "34-hr restart")
        self.assertAlmostEqual(restart.start_min, 2 * 60)


class EmptyTrip(unittest.TestCase):
    """Zero distance: only pickup + dropoff on-duty, no driving."""

    def setUp(self):
        self.plan = plan_trip(0, 0, cycle_used_hours=0)

    def test_only_pickup_dropoff(self):
        self.assertEqual(statuses(self.plan), [DutyStatus.ON_DUTY, DutyStatus.ON_DUTY])
        self.assertEqual(labels(self.plan), ["Pickup", "Dropoff"])
        self.assertAlmostEqual(self.plan.summary["driving_minutes"], 0.0)


class InputValidation(unittest.TestCase):
    def test_negative_miles_rejected(self):
        with self.assertRaises(ValueError):
            plan_trip(-1, 100, 0)

    def test_cycle_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            plan_trip(100, 100, 71)
        with self.assertRaises(ValueError):
            plan_trip(100, 100, -5)


if __name__ == "__main__":
    unittest.main()
