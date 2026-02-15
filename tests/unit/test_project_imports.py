import importlib
import os


def test_package_imports() -> None:
    module = importlib.import_module("triage_automation")
    assert module is not None


def test_apps_modules_import() -> None:
    assert importlib.import_module("apps.bot_api") is not None
    assert importlib.import_module("apps.bot_matrix") is not None
    assert importlib.import_module("apps.worker") is not None


def test_imports_do_not_require_runtime_env_vars(monkeypatch) -> None:
    for env_var in (
        "MATRIX_HOMESERVER_URL",
        "MATRIX_ACCESS_TOKEN",
        "DATABASE_URL",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(env_var, raising=False)

    importlib.invalidate_caches()
    assert importlib.import_module("triage_automation") is not None
    assert importlib.import_module("apps.bot_api") is not None

    # Guard against accidental import-time env reads.
    assert "MATRIX_HOMESERVER_URL" not in os.environ
