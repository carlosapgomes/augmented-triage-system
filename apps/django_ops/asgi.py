"""ASGI config for the django_ops operations web application.

Exposes the ASGI callable as a module-level variable named ``application``.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.django_ops.settings")

application = get_asgi_application()
