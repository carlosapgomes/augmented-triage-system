"""Conftest for Django login/session tests.

Configures Django settings so pytest-django can create
and manage the test database automatically.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.django_ops.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()
