"""URL configuration for the django_ops operations web application.

Defines the top-level URL routing including authentication routes,
role-based landing pages, and the smoke/health endpoint.
"""

from django.urls import path

from apps.django_ops.views import (
    admin_home,
    doctor_home,
    login_view,
    logout_view,
    manager_home,
    manifest_view,
    nir_home,
    root_redirect,
    scheduler_home,
    service_worker_view,
    smoke,
)

urlpatterns = [
    path("", root_redirect, name="root"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("smoke/", smoke, name="smoke"),
    path("nir/", nir_home, name="nir_home"),
    path("doctor/", doctor_home, name="doctor_home"),
    path("scheduler/", scheduler_home, name="scheduler_home"),
    path("manager/", manager_home, name="manager_home"),
    path("admin/", admin_home, name="admin_home"),
    path("manifest.webmanifest", manifest_view, name="manifest"),
    path("service-worker.js", service_worker_view, name="service_worker"),
]
