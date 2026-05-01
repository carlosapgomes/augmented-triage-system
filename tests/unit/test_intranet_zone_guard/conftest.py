"""Conftest for intranet zone guard tests.

Configures Django settings so test database and settings
are available for middleware and view testing.
"""

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.django_ops.settings")

import django
from django.conf import settings

if not settings.configured:
    django.setup()
