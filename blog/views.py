import time

from django.db import connection
from django.http import JsonResponse


def health_check(req):
    """
    Health check endpoint
    """

    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": {},
    }

    try:
        with connection.cursor() as cursor:
            cursor.execute("select 1")
        health["checks"]["database"] = "connected"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = str(e)

    status_code = 200 if health["status"] == "healthy" else 503
    return JsonResponse(health, status=status_code)
