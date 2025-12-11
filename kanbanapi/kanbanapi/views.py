"""Health check views for Kubernetes probes."""

# django ressources
from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.db.utils import OperationalError

# Python default libraries
import time


def health_check(request):
    """
    Basic health check endpoint for liveness probe.
    Returns 200 if the application is running.
    """
    return JsonResponse({"status": "healthy"}, status=200)


def readiness_check(request):
    """
    Readiness check endpoint that verifies database connectivity.
    Returns 200 if the application is ready to serve requests.
    """
    try:
        # Check database connection
        connection.ensure_connection()
        return JsonResponse({"status": "ready", "database": "connected"}, status=200)
    except OperationalError:
        return JsonResponse(
            {"status": "not ready", "database": "disconnected"}, status=503
        )


def metrics(request):
    """
    Prometheus-compatible metrics endpoint for application monitoring.
    Returns metrics in Prometheus text format for scraping.
    Focuses on application health without database-specific metrics.
    """
    metrics_lines = []
    start_time = time.time()

    # Application up metric
    metrics_lines.append("# HELP kanbanapi_up Application is running")
    metrics_lines.append("# TYPE kanbanapi_up gauge")
    metrics_lines.append("kanbanapi_up 1")
    metrics_lines.append("")

    # Database connectivity check (just connection status, not data)
    metrics_lines.append(
        "# HELP kanbanapi_database_available Database connection status (1=connected, 0=disconnected)"
    )
    metrics_lines.append("# TYPE kanbanapi_database_available gauge")
    try:
        connection.ensure_connection()
        metrics_lines.append("kanbanapi_database_available 1")
    except Exception:
        metrics_lines.append("kanbanapi_database_available 0")
    metrics_lines.append("")

    # Metrics generation duration
    generation_time = time.time() - start_time
    metrics_lines.append(
        "# HELP kanbanapi_metrics_generation_duration_seconds Time to generate metrics"
    )
    metrics_lines.append("# TYPE kanbanapi_metrics_generation_duration_seconds gauge")
    metrics_lines.append(
        f"kanbanapi_metrics_generation_duration_seconds {generation_time:.6f}"
    )

    return HttpResponse(
        "\n".join(metrics_lines), content_type="text/plain; version=0.0.4"
    )
