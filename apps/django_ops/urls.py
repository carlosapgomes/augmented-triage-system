"""URL configuration for the django_ops operations web application.

Defines the top-level URL routing including authentication routes,
role-based landing pages, and the smoke/health endpoint.
"""

from django.urls import path

from apps.django_ops.views import (
    admin_home,
    doctor_decision_form,
    doctor_decision_form_submit,
    doctor_home,
    login_view,
    logout_view,
    manager_home,
    manifest_view,
    nir_case_acknowledge_submit,
    nir_case_detail,
    nir_home,
    nir_upload,
    nir_upload_submit,
    root_redirect,
    scheduler_confirmation_form,
    scheduler_confirmation_form_submit,
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
    path("nir/upload/", nir_upload, name="nir_upload"),
    path("nir/upload/submit/", nir_upload_submit, name="nir_upload_submit"),
    path("nir/cases/<uuid:case_id>/", nir_case_detail, name="nir_case_detail"),
    path(
        "nir/cases/<uuid:case_id>/acknowledge/",
        nir_case_acknowledge_submit,
        name="nir_case_acknowledge_submit",
    ),
    path("doctor/", doctor_home, name="doctor_home"),
    path(
        "doctor/cases/<uuid:case_id>/decision/",
        doctor_decision_form,
        name="doctor_decision_form",
    ),
    path(
        "doctor/cases/<uuid:case_id>/decision/submit/",
        doctor_decision_form_submit,
        name="doctor_decision_form_submit",
    ),
    path("scheduler/", scheduler_home, name="scheduler_home"),
    path(
        "scheduler/cases/<uuid:case_id>/confirm/",
        scheduler_confirmation_form,
        name="scheduler_confirmation_form",
    ),
    path(
        "scheduler/cases/<uuid:case_id>/confirm/submit/",
        scheduler_confirmation_form_submit,
        name="scheduler_confirmation_form_submit",
    ),
    path("manager/", manager_home, name="manager_home"),
    path("admin/", admin_home, name="admin_home"),
    path("manifest.webmanifest", manifest_view, name="manifest"),
    path("service-worker.js", service_worker_view, name="service_worker"),
]
