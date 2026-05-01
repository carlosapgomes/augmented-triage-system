"""WSGI config for the django_ops operations web application.

Exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.django_ops.settings")

application = get_wsgi_application()
