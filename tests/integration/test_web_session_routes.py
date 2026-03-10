from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command
from apps.bot_api.main import create_app
from triage_automation.application.services.auth_service import AuthService
from triage_automation.infrastructure.db.auth_event_repository import SqlAlchemyAuthEventRepository
from triage_automation.infrastructure.db.auth_token_repository import SqlAlchemyAuthTokenRepository
from triage_automation.infrastructure.db.session import create_session_factory
from triage_automation.infrastructure.db.user_repository import SqlAlchemyUserRepository
from triage_automation.infrastructure.http.auth_guard import SESSION_COOKIE_NAME
from triage_automation.infrastructure.security.password_hasher import BcryptPasswordHasher
from triage_automation.infrastructure.security.token_service import OpaqueTokenService


def _upgrade_head(tmp_path: Path, filename: str) -> tuple[str, str]:
    db_path = tmp_path / filename
    sync_url = f"sqlite+pysqlite:///{db_path}"
    async_url = f"sqlite+aiosqlite:///{db_path}"

    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(alembic_config, "head")
    return sync_url, async_url


def _insert_user(
    connection: sa.Connection,
    *,
    user_id: UUID,
    email: str,
    password_hash: str,
    role: str = "admin",
) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, email, password_hash, role, is_active) "
            "VALUES (:id, :email, :password_hash, :role, 1)"
        ),
        {
            "id": user_id.hex,
            "email": email,
            "password_hash": password_hash,
            "role": role,
        },
    )


def _build_client(async_url: str, *, token_service: OpaqueTokenService) -> TestClient:
    session_factory = create_session_factory(async_url)
    auth_service = AuthService(
        users=SqlAlchemyUserRepository(session_factory),
        auth_events=SqlAlchemyAuthEventRepository(session_factory),
        password_hasher=BcryptPasswordHasher(),
    )
    token_repository = SqlAlchemyAuthTokenRepository(session_factory)
    app = create_app(
        auth_service=auth_service,
        auth_token_repository=token_repository,
        token_service=token_service,
        database_url=async_url,
    )
    return TestClient(app)


@pytest.mark.asyncio
async def test_root_redirects_to_login_for_anonymous_and_to_dashboard_when_session_exists(
    tmp_path: Path,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "web_session_root_redirects.db")
    hasher = BcryptPasswordHasher()
    token_service = OpaqueTokenService(token_factory=lambda: "web-session-token")
    admin_id = uuid4()

    with sa.create_engine(sync_url).begin() as connection:
        _insert_user(
            connection,
            user_id=admin_id,
            email="admin@example.org",
            password_hash=hasher.hash_password("correct-password"),
        )

    with _build_client(async_url, token_service=token_service) as client:
        anonymous_root = client.get("/", follow_redirects=False)
        login_page = client.get("/login")
        login_response = client.post(
            "/login",
            data={"email": "admin@example.org", "password": "correct-password"},
            follow_redirects=False,
        )
        authenticated_root = client.get("/", follow_redirects=False)

    assert anonymous_root.status_code == 303
    assert anonymous_root.headers["location"] == "/login"
    assert login_page.status_code == 200
    assert login_page.headers["content-type"].startswith("text/html")
    assert '<form method="post" action="/login">' in login_page.text
    assert 'name="email"' in login_page.text
    assert 'name="password"' in login_page.text
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/dashboard/cases"
    assert SESSION_COOKIE_NAME in login_response.headers.get("set-cookie", "")
    assert authenticated_root.status_code == 303
    assert authenticated_root.headers["location"] == "/dashboard/cases"


@pytest.mark.asyncio
async def test_login_page_exposes_pwa_manifest_mobile_metadata_and_service_worker_registration(
    tmp_path: Path,
) -> None:
    _, async_url = _upgrade_head(tmp_path, "web_session_login_pwa_shell.db")

    with _build_client(async_url, token_service=OpaqueTokenService()) as client:
        response = client.get("/login")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<link rel="manifest" href="/manifest.webmanifest">' in response.text
    assert '<meta name="theme-color" content="#0b4263">' in response.text
    assert '<meta name="mobile-web-app-capable" content="yes">' in response.text
    assert '<meta name="apple-mobile-web-app-capable" content="yes">' in response.text
    assert '<meta name="apple-mobile-web-app-title" content="CHD Dashboard">' in response.text
    assert '<meta name="apple-mobile-web-app-status-bar-style" content="default">' in response.text
    assert "if ('serviceWorker' in navigator)" in response.text
    assert "navigator.serviceWorker.register('/service-worker.js')" in response.text


@pytest.mark.asyncio
async def test_pwa_assets_are_published_with_stable_browser_paths(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "web_session_pwa_assets.db")

    with _build_client(async_url, token_service=OpaqueTokenService()) as client:
        manifest_response = client.get("/manifest.webmanifest")
        service_worker_response = client.get("/service-worker.js")
        icon_response = client.get("/pwa/icons/chd-192.png")

    assert manifest_response.status_code == 200
    assert manifest_response.headers["content-type"].startswith("application/manifest+json")
    assert service_worker_response.status_code == 200
    assert service_worker_response.headers["content-type"].startswith("text/javascript")
    assert icon_response.status_code == 200
    assert icon_response.headers["content-type"].startswith("image/png")


@pytest.mark.asyncio
async def test_manifest_declares_dashboard_installability_contract(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "web_session_pwa_manifest_contract.db")

    with _build_client(async_url, token_service=OpaqueTokenService()) as client:
        response = client.get("/manifest.webmanifest")

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "CHD Dashboard"
    assert payload["short_name"] == "CHD"
    assert payload["start_url"] == "/dashboard/cases"
    assert payload["display"] == "standalone"
    assert payload["scope"] == "/"
    assert payload["theme_color"] == "#0b4263"
    assert payload["background_color"] == "#f3f8fb"


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials_without_session_cookie(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "web_session_invalid_credentials.db")
    token_service = OpaqueTokenService()

    with _build_client(async_url, token_service=token_service) as client:
        response = client.post(
            "/login",
            data={"email": "missing@example.org", "password": "wrong"},
        )

    assert response.status_code == 401
    assert response.headers["content-type"].startswith("text/html")
    assert "Credenciais invalidas" in response.text
    assert SESSION_COOKIE_NAME not in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_logout_clears_cookie_and_redirects_to_login(tmp_path: Path) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, "web_session_logout.db")
    hasher = BcryptPasswordHasher()
    token_service = OpaqueTokenService(token_factory=lambda: "logout-session-token")
    admin_id = uuid4()

    with sa.create_engine(sync_url).begin() as connection:
        _insert_user(
            connection,
            user_id=admin_id,
            email="admin@example.org",
            password_hash=hasher.hash_password("correct-password"),
        )

    with _build_client(async_url, token_service=token_service) as client:
        client.post(
            "/login",
            data={"email": "admin@example.org", "password": "correct-password"},
            follow_redirects=False,
        )
        logout_response = client.post("/logout", follow_redirects=False)
        root_after_logout = client.get("/", follow_redirects=False)

    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"
    assert SESSION_COOKIE_NAME in logout_response.headers.get("set-cookie", "")
    assert root_after_logout.status_code == 303
    assert root_after_logout.headers["location"] == "/login"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "expected_prompt_status", "expected_users_status", "expected_user_create_status"),
    [
        ("admin", 200, 200, 303),
        ("reader", 403, 403, 403),
    ],
)
async def test_session_role_matrix_dashboard_allowed_and_prompt_admin_restricted(
    tmp_path: Path,
    role: str,
    expected_prompt_status: int,
    expected_users_status: int,
    expected_user_create_status: int,
) -> None:
    sync_url, async_url = _upgrade_head(tmp_path, f"web_session_role_matrix_{role}.db")
    hasher = BcryptPasswordHasher()
    token_service = OpaqueTokenService(token_factory=lambda: f"{role}-session-token")
    user_id = uuid4()
    email = f"{role}@example.org"

    with sa.create_engine(sync_url).begin() as connection:
        _insert_user(
            connection,
            user_id=user_id,
            email=email,
            password_hash=hasher.hash_password("correct-password"),
            role=role,
        )

    with _build_client(async_url, token_service=token_service) as client:
        login_response = client.post(
            "/login",
            data={"email": email, "password": "correct-password"},
            follow_redirects=False,
        )
        dashboard_response = client.get("/dashboard/cases")
        prompts_response = client.get("/admin/prompts", follow_redirects=False)
        users_page_response = client.get("/admin/users", follow_redirects=False)
        create_user_response = client.post(
            "/admin/users",
            data={
                "email": f"created-{role}@example.org",
                "password": "created-password",
                "role": "reader",
            },
            follow_redirects=False,
        )

    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/dashboard/cases"
    assert dashboard_response.status_code == 200
    assert prompts_response.status_code == expected_prompt_status
    assert users_page_response.status_code == expected_users_status
    assert create_user_response.status_code == expected_user_create_status
    if role == "admin":
        assert prompts_response.headers["content-type"].startswith("text/html")
        assert "Gestao de Prompts" in prompts_response.text
        assert users_page_response.headers["content-type"].startswith("text/html")
        assert "Gestao de Usuarios" in users_page_response.text
        assert create_user_response.headers["location"].startswith("/admin/users")
    else:
        assert prompts_response.json() == {"detail": "admin role required"}
        assert users_page_response.json() == {"detail": "admin role required"}
        assert create_user_response.json() == {"detail": "admin role required"}

    with sa.create_engine(sync_url).begin() as connection:
        total_users = connection.execute(sa.text("SELECT COUNT(*) FROM users")).scalar_one()

    if role == "admin":
        assert int(total_users) == 2
    else:
        assert int(total_users) == 1


@pytest.mark.asyncio
async def test_anonymous_access_to_user_admin_routes_redirects_to_login(tmp_path: Path) -> None:
    _, async_url = _upgrade_head(tmp_path, "web_session_user_admin_anonymous_redirect.db")
    token_service = OpaqueTokenService()
    target_user_id = uuid4()

    with _build_client(async_url, token_service=token_service) as client:
        users_page_response = client.get("/admin/users", follow_redirects=False)
        create_response = client.post(
            "/admin/users",
            data={"email": "anon@example.org", "password": "anon-password", "role": "reader"},
            follow_redirects=False,
        )
        block_response = client.post(
            f"/admin/users/{target_user_id}/block",
            follow_redirects=False,
        )

    assert users_page_response.status_code == 303
    assert users_page_response.headers["location"] == "/login"
    assert create_response.status_code == 303
    assert create_response.headers["location"] == "/login"
    assert block_response.status_code == 303
    assert block_response.headers["location"] == "/login"
