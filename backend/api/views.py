from rest_framework.decorators import api_view
from rest_framework.response import Response


@api_view(['GET'])
def health(request):
    """Simple liveness check so we can confirm the API is wired and running."""
    return Response({'status': 'ok', 'service': 'trip-planner-api'})
