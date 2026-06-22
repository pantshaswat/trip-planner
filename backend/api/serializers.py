"""DRF serializers for the plan-trip endpoint.

The request serializer validates the 4 driver inputs (plus an optional trip
start time). The response serializers exist mainly so drf-spectacular can show
the full output shape in Swagger — they describe, they don't reshape.
"""

from rest_framework import serializers


class TripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(
        max_length=200, help_text="Where the driver is now, e.g. 'Chicago, IL'."
    )
    pickup_location = serializers.CharField(
        max_length=200, help_text="Where the load is picked up."
    )
    dropoff_location = serializers.CharField(
        max_length=200, help_text="Where the load is delivered."
    )
    current_cycle_used = serializers.FloatField(
        min_value=0,
        max_value=70,
        help_text="On-duty hours already used in the rolling 8-day cycle (0-70).",
    )
    start_datetime = serializers.DateTimeField(
        required=False,
        help_text="Optional ISO trip start time. Defaults to now (UTC). "
                  "Used only to lay events onto calendar days for the log sheets.",
    )


# --- Response shape (documentation only) -------------------------------------

class PlaceSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    display_name = serializers.CharField()


class LegSerializer(serializers.Serializer):
    distance_miles = serializers.FloatField()
    geometry = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Ordered [lat, lon] points along the leg.",
    )


class EventSerializer(serializers.Serializer):
    duty_status = serializers.ChoiceField(
        choices=["Driving", "OnDuty", "OffDuty", "Sleeper"]
    )
    start_min = serializers.FloatField(help_text="Minutes from trip start.")
    end_min = serializers.FloatField()
    duration_min = serializers.FloatField()
    label = serializers.CharField()
    miles_marker = serializers.FloatField(
        help_text="Cumulative trip miles where this event begins."
    )


class DaySegmentSerializer(serializers.Serializer):
    duty_status = serializers.CharField()
    start_min = serializers.FloatField(help_text="Minutes since that day's midnight.")
    end_min = serializers.FloatField()
    label = serializers.CharField()


class DayLogSerializer(serializers.Serializer):
    date = serializers.CharField(help_text="YYYY-MM-DD")
    segments = DaySegmentSerializer(many=True)
    totals = serializers.DictField(
        child=serializers.FloatField(), help_text="Minutes per duty status."
    )


class TripResponseSerializer(serializers.Serializer):
    locations = serializers.DictField(child=PlaceSerializer())
    route = serializers.DictField()
    events = EventSerializer(many=True)
    summary = serializers.DictField()
    days = DayLogSerializer(many=True)
    start_datetime = serializers.DateTimeField()
