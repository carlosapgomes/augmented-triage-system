"""Deterministic validation of publication topology documentation.

These tests verify that the publication topology document exists, its English
mirror exists, and that both contain the required topology definitions,
constraints, and validation criteria specified in the
same-host-web-publication-topology and role-zone-network-hardening specs.
"""

from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


# ── Portuguese document ─────────────────────────────────────────────


def test_publication_topology_doc_exists_in_portuguese() -> None:
    doc = _read("docs/publication-topology.md")

    assert "Idioma: **Português (BR)** | [English](en/publication-topology.md)" in doc
    assert "# Topologia de Publicação" in doc


def test_publication_topology_defines_single_host_topology() -> None:
    doc = _read("docs/publication-topology.md")

    assert "Docker rootless" in doc
    assert "mesmo host" in doc
    assert "single-host" in doc


def test_publication_topology_defines_internal_access_path() -> None:
    doc = _read("docs/publication-topology.md")

    assert "## Caminhos de Acesso" in doc
    assert "### Acesso Interno" in doc
    assert "127.0.0.1:8001" in doc


def test_publication_topology_defines_external_access_via_cloudflare_tunnel() -> None:
    doc = _read("docs/publication-topology.md")

    assert "### Acesso Externo" in doc
    assert "Cloudflare Tunnel" in doc


def test_publication_topology_documents_backend_services_never_exposed() -> None:
    doc = _read("docs/publication-topology.md")

    assert "bot-api" in doc
    assert "nunca exposto" in doc
    assert "8000" in doc
    assert "5432" in doc


def test_publication_topology_documents_django_as_only_surface() -> None:
    doc = _read("docs/publication-topology.md")

    assert "django-ops" in doc
    assert "8001" in doc
    assert "única superfície humana" in doc
    assert "FastAPI" in doc


def test_publication_topology_defines_role_access_matrix_for_internal_access() -> None:
    doc = _read("docs/publication-topology.md")

    assert "## Matriz de Acesso por Papel e Zona" in doc
    assert "nir" in doc
    assert "doctor" in doc
    assert "scheduler" in doc
    assert "manager" in doc
    assert "admin" in doc
    # Verify diagram uses role-prefixed Django paths, not legacy /dashboard/*
    assert "/manager/*" in doc
    assert "/admin/*" in doc
    assert "/nir/*" in doc
    assert "/doctor/*" in doc
    assert "/scheduler/*" in doc
    assert "/dashboard/*" not in doc


def test_publication_topology_blocks_nir_on_external_path() -> None:
    doc = _read("docs/publication-topology.md")

    assert "Bloqueado no túnel/proxy" in doc
    # nir should appear with blocked external access
    assert "nir" in doc


def test_publication_topology_blocks_scheduler_on_external_path() -> None:
    doc = _read("docs/publication-topology.md")

    # scheduler should be listed as blocked externally
    lines_with_scheduler_blocked = [
        line
        for line in doc.splitlines()
        if "scheduler" in line.lower() and "bloqueado" in line.lower()
    ]
    assert lines_with_scheduler_blocked


def test_publication_topology_allows_doctor_manager_admin_external() -> None:
    doc = _read("docs/publication-topology.md")

    assert "Via Cloudflare Tunnel" in doc


def test_publication_topology_defines_validation_criteria() -> None:
    doc = _read("docs/publication-topology.md")

    assert "## Critérios de Validação" in doc


def test_publication_topology_validation_criteria_covers_backend_ports() -> None:
    doc = _read("docs/publication-topology.md")

    assert "ss -tlnp" in doc
    assert "8000" in doc
    assert "5432" in doc


def test_publication_topology_validation_criteria_covers_external_role_restriction() -> None:
    doc = _read("docs/publication-topology.md")

    assert "curl" in doc
    assert "403" in doc
    assert "nir" in doc
    assert "scheduler" in doc


def test_publication_topology_validation_criteria_covers_https() -> None:
    doc = _read("docs/publication-topology.md")

    assert "HTTPS" in doc
    assert "301" in doc


def test_publication_topology_defines_topology_decisions() -> None:
    doc = _read("docs/publication-topology.md")

    assert "## Decisões de Topologia" in doc
    assert "Single-host como baseline" in doc


def test_publication_topology_references_hardening_checklist() -> None:
    doc = _read("docs/publication-topology.md")

    assert "zone-hardening-checklist.md" in doc


def test_publication_topology_defines_conscious_limitations() -> None:
    doc = _read("docs/publication-topology.md")

    assert "## Limitações Conscientes" in doc
    assert "não há suporte para" in doc


def test_publication_topology_does_not_describe_troubleshooting_sprawl() -> None:
    doc = _read("docs/publication-topology.md")

    assert "## Troubleshooting" not in doc


def test_publication_topology_does_not_support_legacy_surfaces() -> None:
    doc = _read("docs/publication-topology.md")

    assert "Superfícies legadas fora do escopo" in doc
    assert "não são superfícies de publicação" in doc


# ── English mirror ──────────────────────────────────────────────────


def test_publication_topology_doc_exists_in_english() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert (
        "Language: [Portugues (BR)](../publication-topology.md) | **English**"
        in doc
    )
    assert "# Publication Topology" in doc


def test_publication_topology_english_defines_access_matrix() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert "## Access Matrix by Role and Zone" in doc
    assert "nir" in doc
    assert "doctor" in doc
    assert "scheduler" in doc
    assert "manager" in doc
    assert "admin" in doc
    # Verify diagram uses role-prefixed Django paths, not legacy /dashboard/*
    assert "/manager/*" in doc
    assert "/admin/*" in doc
    assert "/nir/*" in doc
    assert "/doctor/*" in doc
    assert "/scheduler/*" in doc
    assert "/dashboard/*" not in doc


def test_publication_topology_english_blocks_nir_and_scheduler_externally() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert "Blocked at tunnel/proxy" in doc


def test_publication_topology_english_defines_validation_criteria() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert "## Validation Criteria" in doc
    assert "ss -tlnp" in doc
    assert "curl" in doc
    assert "403" in doc
    assert "HTTPS" in doc


def test_publication_topology_english_defines_topology_decisions() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert "## Topology Decisions" in doc
    assert "single-host" in doc
    assert "Cloudflare Tunnel as the only remote path" in doc


def test_publication_topology_english_references_hardening_checklist() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert "zone-hardening-checklist.md" in doc


def test_publication_topology_english_defines_conscious_limitations() -> None:
    doc = _read("docs/en/publication-topology.md")

    assert "## Conscious Limitations" in doc
    assert "no support" in doc


# ── Bilingual mirror structural checks ──────────────────────────────


def test_publication_topology_is_in_bilingual_mirror_index() -> None:
    docs_names = {path.name for path in Path("docs").glob("*.md")}
    docs_en_names = {path.name for path in Path("docs/en").glob("*.md")}

    assert "publication-topology.md" in docs_names
    assert "publication-topology.md" in docs_en_names
