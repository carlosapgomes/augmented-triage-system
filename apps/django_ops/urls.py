"""URL configuration for the django_ops operations web application.

Defines the top-level URL routing including the smoke/health endpoint.
"""

from django.urls import path

from apps.django_ops.views import smoke

urlpatterns = [
    path("smoke/", smoke, name="smoke"),
]
