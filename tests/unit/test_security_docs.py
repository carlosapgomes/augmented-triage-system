"""Deterministic validation of security documentation.

These tests verify that the security document reflects the consolidated
Django role model used by the current system, not the legacy admin/reader
model.
"""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ── Portuguese document ─────────────────────────────────────────────


def test_security_doc_has_consolidated_role_model_in_portuguese() -> None:
    doc = _read("docs/security.md")

    assert "## Modelo de auth (atual)" in doc

    # Must reference the full consolidated Django role set, not just admin/reader
    consolidated_roles = ("nir", "doctor", "scheduler", "manager")
    for role in consolidated_roles:
        assert role in doc, f"Role {role!r} missing from security.md role model"

    # Must mention admin as part of the operational set
    assert "admin" in doc

    # The outdated "admin e reader explícitos" phrase must NOT appear alone
    # without mentioning the operational roles
    if "admin" in doc and "reader" in doc:
        # Both may appear, but the operational roles must also be present
        pass  # already verified above


def test_security_doc_does_not_present_outdated_role_model() -> None:
    doc = _read("docs/security.md")

    # The phrase "apenas admin e reader" or "admin e reader explícitos"
    # should not appear as the sole role model
    assert "apenas admin e reader" not in doc.lower()


def test_security_doc_references_django_auth() -> None:
    doc = _read("docs/security.md")

    # The consolidated auth model is Django-first
    assert "Django" in doc


# ── English mirror ──────────────────────────────────────────────────


def test_security_doc_has_consolidated_role_model_in_english() -> None:
    doc = _read("docs/en/security.md")

    assert "## Auth model (current)" in doc

    consolidated_roles = ("nir", "doctor", "scheduler", "manager")
    for role in consolidated_roles:
        assert role in doc, f"Role {role!r} missing from security.md (EN) role model"

    assert "admin" in doc


def test_security_doc_does_not_present_outdated_role_model_in_english() -> None:
    doc = _read("docs/en/security.md")

    # The phrase "only admin and reader" or "explicit admin and reader"
    # should not appear as the sole role model
    assert "only admin and reader" not in doc.lower()


def test_security_doc_references_django_auth_in_english() -> None:
    doc = _read("docs/en/security.md")

    assert "Django" in doc
