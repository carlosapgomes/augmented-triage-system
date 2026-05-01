"""Django settings for the django_ops operations web application.

Minimal configuration to boot the Django app independently from
the existing FastAPI runtime.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR: Path = Path(__file__).resolve().parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY: str = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-change-me-in-production",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG: bool = False

ALLOWED_HOSTS: list[str] = ["*"]

# Application definition
INSTALLED_APPS: list[str] = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "apps.django_ops",
]

MIDDLEWARE: list[str] = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.django_ops.zone_guard.IntranetZoneGuardMiddleware",
]

ROOT_URLCONF: str = "apps.django_ops.urls"

TEMPLATES: list[dict[str, object]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION: str = "apps.django_ops.wsgi.application"

# Database — placeholder; actual DB integration happens in later slices.
DATABASES: dict[str, dict[str, str]] = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "db.sqlite3"),
    }
}

# Internationalization
LANGUAGE_CODE: str = "pt-br"
TIME_ZONE: str = "America/Sao_Paulo"
USE_I18N: bool = True
USE_TZ: bool = True

# Static files (CSS, JavaScript, Images)
STATIC_URL: str = "static/"

# Default primary key field type
DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL: str = "django_ops.User"

# Trusted proxy configuration for client IP resolution.
# Only IP addresses listed here will have their X-Forwarded-For headers
# trusted by the IP resolver. Leave empty to trust no proxies.
TRUSTED_PROXIES: list[str] = []

# Intranet CIDR allowlist for zone-based access restrictions.
# Only roles in INTRANET_ONLY_ROLES (nir, scheduler) are affected.
# These roles must access the application from an IP within one of
# these CIDRs. Defaults to loopback for development/testing.
# In production, override with the actual intranet CIDR range.
INTRANET_CIDR_ALLOWLIST: list[str] = ["127.0.0.0/8"]

# Authentication URLs
LOGIN_URL: str = "/login/"
LOGOUT_REDIRECT_URL: str = "/login/"

# Authentication backends
AUTHENTICATION_BACKENDS: list[str] = [
    "apps.django_ops.auth_backends.EmailBackend",
]
