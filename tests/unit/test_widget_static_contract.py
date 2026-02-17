from pathlib import Path

INDEX_PATH = Path("apps/bot_api/static/widget/room2/index.html")
APP_JS_PATH = Path("apps/bot_api/static/widget/room2/app.js")
STYLES_PATH = Path("apps/bot_api/static/widget/room2/styles.css")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_widget_static_assets_exist_and_are_linked() -> None:
    assert INDEX_PATH.exists()
    assert APP_JS_PATH.exists()
    assert STYLES_PATH.exists()

    index = _read(INDEX_PATH)

    assert '<html lang="pt-BR">' in index
    assert '<link rel="stylesheet" href="/widget/room2/styles.css">' in index
    assert '<script src="/widget/room2/app.js" defer></script>' in index


def test_widget_static_form_contract_and_pt_br_labels() -> None:
    index = _read(INDEX_PATH)

    assert "Widget de decisao medica" in index
    assert "Entrar" in index
    assert "Carregar caso" in index
    assert "Enviar decisao" in index

    assert 'id="login-email"' in index
    assert 'id="login-password"' in index
    assert 'id="case-id"' in index
    assert 'id="doctor-user-id"' in index
    assert 'id="decision"' in index
    assert 'id="support-flag"' in index
    assert 'id="reason"' in index


def test_widget_app_js_uses_required_endpoints_and_payload_shape() -> None:
    app_js = _read(APP_JS_PATH)

    assert "const LOGIN_ENDPOINT = '/auth/login';" in app_js
    assert "const BOOTSTRAP_ENDPOINT = '/widget/room2/bootstrap';" in app_js
    assert "const SUBMIT_ENDPOINT = '/widget/room2/submit';" in app_js

    assert "case_id:" in app_js
    assert "doctor_user_id:" in app_js
    assert "decision:" in app_js
    assert "support_flag:" in app_js
    assert "reason:" in app_js

    assert "x-signature" not in app_js
    assert "WEBHOOK_HMAC_SECRET" not in app_js


def test_widget_app_js_enforces_support_flags_and_deterministic_error_mapping() -> None:
    app_js = _read(APP_JS_PATH)

    assert "const ALLOWED_SUPPORT_FLAGS = ['none', 'anesthesist', 'anesthesist_icu'];" in app_js

    assert "function mapApiError(statusCode)" in app_js
    assert "case 401:" in app_js
    assert "case 403:" in app_js
    assert "case 404:" in app_js
    assert "case 409:" in app_js
    assert "default:" in app_js
