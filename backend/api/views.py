from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import TripRequestSerializer, TripResponseSerializer
from .services import GeocodingError, RoutingError
from .services import planner


@extend_schema(responses=OpenApiTypes.OBJECT, summary="Liveness check")
@api_view(["GET"])
def health(request):
    """Simple liveness check so we can confirm the API is wired and running."""
    return Response({"status": "ok", "service": "trip-planner-api"})


def _serialize(result) -> dict:
    """Turn the planner's dataclasses into plain JSON-ready dicts."""
    combined_geometry = result.leg1.geometry + result.leg2.geometry
    return {
        "locations": {
            "current": vars(result.current),
            "pickup": vars(result.pickup),
            "dropoff": vars(result.dropoff),
        },
        "route": {
            "legs": [
                {"distance_miles": result.leg1.distance_miles, "geometry": result.leg1.geometry},
                {"distance_miles": result.leg2.distance_miles, "geometry": result.leg2.geometry},
            ],
            "geometry": combined_geometry,
            "total_distance_miles": result.leg1.distance_miles + result.leg2.distance_miles,
        },
        "events": [e.to_dict() for e in result.plan.events],
        "summary": result.plan.summary,
        "days": [vars(d) for d in result.days],
        "start_datetime": result.start_datetime.isoformat(),
    }


@extend_schema(
    request=TripRequestSerializer,
    responses={200: TripResponseSerializer},
    summary="Plan a trip and generate ELD logs",
    description=(
        "Geocodes the three locations, routes the two legs, runs the HOS "
        "simulation, and returns the route geometry, the ordered duty-event "
        "list, and per-calendar-day log data."
    ),
    examples=[
        OpenApiExample(
            "Chicago to St. Louis",
            value={
                "current_location": "Chicago, IL",
                "pickup_location": "Joliet, IL",
                "dropoff_location": "St. Louis, MO",
                "current_cycle_used": 10,
            },
            request_only=True,
        ),
    ],
)
@api_view(["POST"])
def plan_trip(request):
    """Plan the whole trip in advance and return route + events + day logs."""
    req = TripRequestSerializer(data=request.data)
    req.is_valid(raise_exception=True)
    data = req.validated_data

    try:
        result = planner.plan(
            current_location=data["current_location"],
            pickup_location=data["pickup_location"],
            dropoff_location=data["dropoff_location"],
            current_cycle_used=data["current_cycle_used"],
            start_datetime=data.get("start_datetime"),
        )
    except GeocodingError as exc:
        # Bad/unresolvable location -> client error.
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except RoutingError as exc:
        # Upstream routing failure -> bad gateway.
        return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(_serialize(result), status=status.HTTP_200_OK)
