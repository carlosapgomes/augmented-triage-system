"""Manage.py entrypoint for the django_ops operations web application."""

import os
import sys


def main() -> None:
    """Run administrative tasks for the Django operations app."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apps.django_ops.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
