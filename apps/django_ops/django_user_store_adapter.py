"""Django ORM adapter implementing ``DjangoUserStorePort``.

Bridges between the application-layer port and Django's ORM so
the application service never imports Django models directly.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model

from triage_automation.application.ports.django_user_store_port import (
    DjangoUserItem,
    DjangoUserStorePort,
)

User = get_user_model()


class DjangoOrmUserStoreAdapter(DjangoUserStorePort):
    """Django-ORM-backed implementation of the user store port."""

    def list_users(self) -> list[DjangoUserItem]:
        """Return all users ordered by email."""

        return [
            DjangoUserItem(
                pk=user.pk,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
            )
            for user in User.objects.order_by("email")
        ]

    def get_by_pk(self, *, pk: int) -> DjangoUserItem | None:
        """Return one user by primary key, or None."""

        user = User.objects.filter(pk=pk).first()
        if user is None:
            return None
        return DjangoUserItem(
            pk=user.pk,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )

    def create_user(
        self, *, email: str, password: str, role: str
    ) -> DjangoUserItem:
        """Persist a new user account and return it."""

        created = User.objects.create_user(
            email=email,
            password=password,
            role=role,
        )
        return DjangoUserItem(
            pk=created.pk,
            email=created.email,
            role=created.role,
            is_active=created.is_active,
        )

    def email_exists(self, *, email: str) -> bool:
        """Return True if a user with the given email exists (case-insensitive)."""

        return User.objects.filter(email__iexact=email).exists()  # type: ignore[no-any-return]

    def update_role(self, *, pk: int, role: str) -> DjangoUserItem:
        """Persist a new role value for an existing user."""

        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise ValueError(f"user not found: {pk}")
        user.role = role
        user.save(update_fields=["role", "updated_at"])
        return DjangoUserItem(
            pk=user.pk,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )

    def set_active(self, *, pk: int, is_active: bool) -> DjangoUserItem:
        """Persist the active flag for an existing user."""

        user = User.objects.filter(pk=pk).first()
        if user is None:
            raise ValueError(f"user not found: {pk}")
        user.is_active = is_active
        user.save(update_fields=["is_active", "updated_at"])
        return DjangoUserItem(
            pk=user.pk,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
        )

    def count_active_by_role(self, *, role: str) -> int:
        """Return the count of active users with the given role."""

        return User.objects.filter(role=role, is_active=True).count()  # type: ignore[no-any-return]
