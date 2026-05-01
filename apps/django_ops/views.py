"""Minimal views for the django_ops operations web application."""

from django.http import HttpRequest, JsonResponse


def smoke(request: HttpRequest) -> JsonResponse:
    """Health/smoke endpoint to validate Django app is running.

    Returns a JSON response with status ``ok`` so monitoring and
    deployment checks can confirm the app is healthy.
    """
    return JsonResponse({"status": "ok"})
