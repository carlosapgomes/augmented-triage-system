"""Deterministic validation of zone hardening checklist documentation.

These tests verify that the zone hardening checklist document exists,
its English mirror exists, and that both contain the required hardening
checklists, role/zone access validation steps, and troubleshooting
guidance specified in the role-zone-network-hardening spec.
"""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ── Portuguese document ─────────────────────────────────────────────


def test_zone_hardening_checklist_doc_exists_in_portuguese() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert (
        "Idioma: **Português (BR)** | [English](en/zone-hardening-checklist.md)"
        in doc
    )
    assert "# Checklist de Hardening por Zona e Papel" in doc


def test_zone_hardening_checklist_documents_intranet_only_role_denial() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    # nir denial outside intranet MUST be explicitly validated
    assert "nir" in doc
    assert "bloqueado" in doc.lower() or "negado" in doc.lower()
    assert "externo" in doc.lower() or "externamente" in doc.lower()
    # scheduler denial outside intranet MUST be explicitly validated
    assert "scheduler" in doc
    lines_with_scheduler_denied = [
        line
        for line in doc.splitlines()
        if "scheduler" in line.lower()
        and ("bloqueado" in line.lower() or "negado" in line.lower())
    ]
    assert lines_with_scheduler_denied


def test_zone_hardening_checklist_documents_remote_role_access() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    # doctor remote access MUST be explicitly validated
    assert "doctor" in doc
    lines_doctor_remote = [
        line
        for line in doc.splitlines()
        if "doctor" in line.lower() and "remoto" in line.lower()
    ]
    assert lines_doctor_remote
    # manager remote access MUST be explicitly validated
    assert "manager" in doc
    # admin remote access MUST be explicitly validated
    assert "admin" in doc
    # Cloudflare Tunnel reference for remote access
    assert "Cloudflare Tunnel" in doc


def test_zone_hardening_checklist_has_role_zone_matrix() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "## Matriz de Verificação por Papel e Zona" in doc
    # All five roles must appear
    for role in ("nir", "doctor", "scheduler", "manager", "admin"):
        assert role in doc


def test_zone_hardening_checklist_has_deterministic_validation_steps() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "## Passos de Validação" in doc
    # Deterministic commands should be present
    assert "curl" in doc
    assert "http_code" in doc or "http%" in doc


def test_zone_hardening_checklist_has_troubleshooting_section() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "## Troubleshooting" in doc
    assert "diagnóstico" in doc.lower() or "diagnostic" in doc.lower()


def test_zone_hardening_checklist_documents_access_denial_troubleshooting() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    # Must document what to do when allowed role is denied access
    assert "permitido" in doc.lower() or "permissão" in doc.lower()
    # Must document what to do when intranet-only role is reachable externally
    assert "acessível" in doc.lower() or "alcançável" in doc.lower()


def test_zone_hardening_checklist_defines_escalation_criteria() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "escalonamento" in doc.lower() or "escalar" in doc.lower()
    assert "desenvolvimento" in doc.lower()


def test_zone_hardening_checklist_references_publication_topology() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "publication-topology.md" in doc


def test_zone_hardening_checklist_has_hardening_verification_commands() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    # Must contain hardening/denial verification commands for nir and scheduler
    assert "403" in doc or "404" in doc


def test_zone_hardening_checklist_has_internal_access_verification() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "127.0.0.1:8001" in doc
    assert "interno" in doc.lower() or "intranet" in doc.lower()


def test_zone_hardening_checklist_has_cloudflare_tunnel_verification() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    assert "túnel" in doc.lower() or "tunnel" in doc.lower()


def test_zone_hardening_checklist_no_legacy_surface_operational_dependency() -> None:
    doc = _read("docs/zone-hardening-checklist.md")

    # Must NOT reintroduce operational dependency on legacy human surfaces.
    # FastAPI may appear only in the disclaimer header ("não reintroduz dependência
    # operacional de superfícies humanas legadas (FastAPI, Matrix)").
    fastapi_lines = [line for line in doc.splitlines() if "FastAPI" in line]
    for line in fastapi_lines:
        assert ("não reintroduz" in line or "legadas" in line or "legacy" in line
                or "disclaimer" in line.lower()), (
            f"FastAPI must not appear outside disclaimer context: {line}"
        )
    # bot-matrix must not appear as an operational surface
    assert "bot-matrix" not in doc
    # bot-api may appear only in hardening/validation context (port checks),
    # never as an access-path instruction like "navigate to bot-api" or
    # "access bot-api at http://".
    assert "bot-api" in doc  # allowed in port-listen checks
    for line in doc.splitlines():
        if "bot-api" in line:
            # Must not suggest accessing bot-api as an operational path
            assert "http://" not in line, (
                f"bot-api must not be presented as an operational URL: {line}"
            )


def test_zone_hardening_checklist_no_legacy_matrix_operational_dependency() -> None:
    _ = _read("docs/zone-hardening-checklist.md")

    # Must NOT reference Matrix as an operational surface for human access.
    # "Matrix" alone is a common word; ensure bot-matrix is not presented
    # as an operational access path. Already covered in the previous test.
    pass


# ── English mirror ──────────────────────────────────────────────────


def test_zone_hardening_checklist_doc_exists_in_english() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert (
        "Language: [Portugues (BR)](../zone-hardening-checklist.md) | **English**"
        in doc
    )
    assert "# Zone and Role Hardening Checklist" in doc


def test_zone_hardening_checklist_english_documents_intranet_only_denial() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "nir" in doc
    assert "blocked" in doc.lower() or "denied" in doc.lower()
    assert "scheduler" in doc


def test_zone_hardening_checklist_english_documents_remote_role_access() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "doctor" in doc
    assert "manager" in doc
    assert "admin" in doc
    assert "Cloudflare Tunnel" in doc


def test_zone_hardening_checklist_english_has_role_zone_matrix() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "## Verification Matrix by Role and Zone" in doc
    for role in ("nir", "doctor", "scheduler", "manager", "admin"):
        assert role in doc


def test_zone_hardening_checklist_english_has_deterministic_validation() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "## Validation Steps" in doc
    assert "curl" in doc


def test_zone_hardening_checklist_english_has_troubleshooting() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "## Troubleshooting" in doc
    assert "diagnosis" in doc.lower() or "diagnostic" in doc.lower()


def test_zone_hardening_checklist_english_defines_escalation() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "escalation" in doc.lower()
    assert "development" in doc.lower()


def test_zone_hardening_checklist_english_references_publication_topology() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    assert "publication-topology.md" in doc


def test_zone_hardening_checklist_english_no_legacy_surface_dependency() -> None:
    doc = _read("docs/en/zone-hardening-checklist.md")

    # Must NOT reintroduce operational dependency on legacy human surfaces.
    # FastAPI may appear only in the disclaimer header.
    fastapi_lines = [line for line in doc.splitlines() if "FastAPI" in line]
    for line in fastapi_lines:
        assert ("does not reintroduce" in line or "legacy" in line
                or "legadas" in line or "disclaimer" in line.lower()), (
            f"FastAPI must not appear outside disclaimer context: {line}"
        )
    assert "bot-matrix" not in doc
    # bot-api allowed only in hardening context (port checks)
    assert "bot-api" in doc
    for line in doc.splitlines():
        if "bot-api" in line:
            assert "http://" not in line, (
                f"bot-api must not be presented as an operational URL: {line}"
            )


# ── Bilingual mirror structural checks ──────────────────────────────


def test_zone_hardening_checklist_is_in_bilingual_mirror_index() -> None:
    docs_names = {path.name for path in Path("docs").glob("*.md")}
    docs_en_names = {path.name for path in Path("docs/en").glob("*.md")}

    assert "zone-hardening-checklist.md" in docs_names
    assert "zone-hardening-checklist.md" in docs_en_names
