"""Authentication backend for the django_ops application.

Uses email-based authentication with the custom User model
instead of Django's default username-based authentication.
"""

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):  # type: ignore[misc]
    """Authenticate using email and password.

    Overrides the default ModelBackend to use email as the
    primary identifier field for authentication.
    """

    def authenticate(
        self,
        request: Any = None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate a user by email and password.

        Args:
            request: The HTTP request (unused in this backend).
            username: The email address to authenticate.
            password: The plaintext password to verify.
            **kwargs: Additional keyword arguments (ignored).

        Returns:
            The authenticated User instance, or None if authentication fails.
        """
        if username is None or password is None:
            return None
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            # Run the password hasher to reduce timing attack surface
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
