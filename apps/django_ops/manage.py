"""Manage.py entrypoint for the django_ops operations web application.

Adds the repository root to ``sys.path`` so that the
``apps.django_ops`` package remains importable regardless of
the working directory from which this script is invoked.
"""

import os
import sys
from pathlib import Path

# Repository root (two levels up: django_ops -> apps -> repo root).
_REPO_ROOT: str = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


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
