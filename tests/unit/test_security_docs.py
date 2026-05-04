"""Deterministic validation of security documentation.

These tests verify that the security document reflects the consolidated
Django role model used by the current system — only the five operational
roles — and that `reader` is not presented as a current retained role.
"""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

OP_ROLES = ("nir", "doctor", "scheduler", "manager", "admin")


# ── Portuguese document ─────────────────────────────────────────────


def test_security_doc_has_consolidated_role_model_in_portuguese() -> None:
    doc = _read("docs/security.md")

    assert "## Modelo de auth (atual)" in doc

    # All five operational roles must appear
    for role in OP_ROLES:
        assert role in doc, f"Operational role {role!r} missing from security.md"


def test_security_doc_current_role_model_is_only_operational_roles() -> None:
    doc = _read("docs/security.md")

    # Find the role model section and collect consecutive continuation lines
    lines = doc.splitlines()
    role_block = ""
    in_role = False
    for line in lines:
        if "Modelo de papéis" in line:
            in_role = True
            role_block = line
        elif in_role:
            # Continuation lines start with whitespace after a bullet
            if line.startswith("  ") or line.startswith("\t"):
                role_block += " " + line.strip()
            else:
                break

    # The current role model must ONLY list operational roles
    for role in OP_ROLES:
        assert role in role_block, (
            f"Operational role {role!r} missing from role model: {role_block}"
        )
    # reader must NOT appear in the current role model
    assert "reader" not in role_block, (
        f"'reader' must not be in the current role model: {role_block}"
    )


def test_security_doc_reader_only_as_historical_if_present() -> None:
    doc = _read("docs/security.md")

    if "reader" in doc:
        # If reader appears at all, it must be in historical/migration context
        reader_lines = [line for line in doc.splitlines() if "reader" in line.lower()]
        assert reader_lines, "reader found but unexpected parsing error"

        # "mantido" or "retido" must NOT appear with reader
        for line in reader_lines:
            assert "mantido" not in line.lower(), (
                f"'reader' must not be described as retained/kept: {line}"
            )
            assert "retido" not in line.lower(), (
                f"'reader' must not be described as retained/kept: {line}"
            )
            # If mentioned, must be in historical/migration context
            assert any(kw in line.lower() for kw in (
                "mapeado", "migrado", "legado", "histórico",
                "mapped", "migrated", "legacy", "historical",
            )), f"'reader' mentioned without historical context: {line}"


def test_security_doc_does_not_present_outdated_role_model() -> None:
    doc = _read("docs/security.md")

    assert "apenas admin e reader" not in doc.lower()
    # The old "admin e reader explícitos" phrase must not appear
    assert "admin e reader explícitos" not in doc


def test_security_doc_references_django_auth() -> None:
    doc = _read("docs/security.md")

    assert "Django" in doc


# ── English mirror ──────────────────────────────────────────────────


def test_security_doc_has_consolidated_role_model_in_english() -> None:
    doc = _read("docs/en/security.md")

    assert "## Auth model (current)" in doc

    for role in OP_ROLES:
        assert role in doc, f"Operational role {role!r} missing from security.md (EN)"


def test_security_doc_current_role_model_is_only_operational_roles_en() -> None:
    doc = _read("docs/en/security.md")

    lines = doc.splitlines()
    role_block = ""
    in_role = False
    for line in lines:
        if "Role model" in line:
            in_role = True
            role_block = line
        elif in_role:
            if line.startswith("  ") or line.startswith("\t"):
                role_block += " " + line.strip()
            else:
                break

    for role in OP_ROLES:
        assert role in role_block, (
            f"Operational role {role!r} missing from role model (EN): {role_block}"
        )
    assert "reader" not in role_block, (
        f"'reader' must not be in the current role model (EN): {role_block}"
    )


def test_security_doc_reader_only_as_historical_if_present_en() -> None:
    doc = _read("docs/en/security.md")

    if "reader" in doc:
        reader_lines = [line for line in doc.splitlines() if "reader" in line.lower()]
        assert reader_lines, "reader found but unexpected parsing error"

        for line in reader_lines:
            assert "retained" not in line.lower(), (
                f"'reader' must not be described as retained/kept (EN): {line}"
            )
            assert "kept" not in line.lower(), (
                f"'reader' must not be described as retained/kept (EN): {line}"
            )
            assert any(kw in line.lower() for kw in (
                "mapped", "migrated", "legacy", "historical",
            )), f"'reader' mentioned without historical context (EN): {line}"


def test_security_doc_does_not_present_outdated_role_model_in_english() -> None:
    doc = _read("docs/en/security.md")

    assert "only admin and reader" not in doc.lower()
    # The old "explicit admin and reader" phrase must not appear
    assert "explicit admin and reader" not in doc


def test_security_doc_references_django_auth_in_english() -> None:
    doc = _read("docs/en/security.md")

    assert "Django" in doc
