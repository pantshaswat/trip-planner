"""View-layer tests for /api/plan-trip/. The planner (network) is mocked,
so these run offline and fast. Engine + service logic is tested elsewhere.
"""

from datetime import datetime, timezone
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APITestCase

from .hos import plan_trip as run_engine
from .services.errors import GeocodingError, RoutingError
from .services.geocoding import Place
from .services.planner import TripResult, _slice_into_days
from .services.routing import RouteLeg


def _fake_result():
    """A small, deterministic TripResult without touching the network."""
    plan = run_engine(55, 55, 0)  # tiny trip: drive, pickup, drive, dropoff
    start = datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)
    return TripResult(
        current=Place(41.88, -87.62, "Chicago, IL"),
        pickup=Place(41.52, -88.08, "Joliet, IL"),
        dropoff=Place(38.63, -90.20, "St. Louis, MO"),
        leg1=RouteLeg(55.0, [[41.88, -87.62], [41.52, -88.08]]),
        leg2=RouteLeg(55.0, [[41.52, -88.08], [38.63, -90.20]]),
        plan=plan,
        days=_slice_into_days(plan, start),
        start_datetime=start,
    )


class PlanTripViewTests(APITestCase):
    URL = "/api/plan-trip/"
    PAYLOAD = {
        "current_location": "Chicago, IL",
        "pickup_location": "Joliet, IL",
        "dropoff_location": "St. Louis, MO",
        "current_cycle_used": 10,
    }

    @patch("api.views.planner.plan")
    def test_success_shape(self, mock_plan):
        mock_plan.return_value = _fake_result()
        resp = self.client.post(self.URL, self.PAYLOAD, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(
            set(body),
            {"locations", "route", "events", "summary", "days", "start_datetime"},
        )
        self.assertEqual(body["route"]["total_distance_miles"], 110.0)
        self.assertEqual(len(body["events"]), 4)
        self.assertEqual(body["locations"]["current"]["display_name"], "Chicago, IL")

    def test_missing_field_rejected(self):
        bad = {k: v for k, v in self.PAYLOAD.items() if k != "dropoff_location"}
        resp = self.client.post(self.URL, bad, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cycle_out_of_range_rejected(self):
        bad = {**self.PAYLOAD, "current_cycle_used": 99}
        resp = self.client.post(self.URL, bad, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("api.views.planner.plan", side_effect=GeocodingError("no match"))
    def test_geocoding_error_is_400(self, _mock):
        resp = self.client.post(self.URL, self.PAYLOAD, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", resp.json())

    @patch("api.views.planner.plan", side_effect=RoutingError("no route"))
    def test_routing_error_is_502(self, _mock):
        resp = self.client.post(self.URL, self.PAYLOAD, format="json")
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)


class DaySlicingTests(APITestCase):
    """The midnight-crossing logic for log sheets."""

    def test_event_crossing_midnight_is_split(self):
        # Long single leg guarantees multi-day, midnight-crossing events.
        plan = run_engine(1500, 0, 0)
        start = datetime(2026, 6, 22, 20, 0, tzinfo=timezone.utc)  # 8pm start
        days = _slice_into_days(plan, start)
        self.assertGreaterEqual(len(days), 2)
        for day in days:
            day_total = sum(s["end_min"] - s["start_min"] for s in day.segments)
            # No day holds more than 24h of activity.
            self.assertLessEqual(day_total, 24 * 60 + 1e-6)
            for seg in day.segments:
                self.assertGreaterEqual(seg["start_min"], 0)
                self.assertLessEqual(seg["end_min"], 24 * 60 + 1e-6)
