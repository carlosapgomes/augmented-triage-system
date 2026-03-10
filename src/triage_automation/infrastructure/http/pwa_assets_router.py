"""FastAPI router exposing static PWA assets with stable browser paths."""

from __future__ import annotations

from pathlib import Path, PurePath

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

_PWA_STATIC_DIR = Path(__file__).resolve().parent / "static" / "pwa"
_ICONS_DIR = _PWA_STATIC_DIR / "icons"


def build_pwa_assets_router() -> APIRouter:
    """Build router that serves PWA manifest, service worker, and icon assets."""

    router = APIRouter(tags=["pwa-assets"])

    @router.get("/manifest.webmanifest", include_in_schema=False)
    async def get_manifest() -> FileResponse:
        return _build_file_response(
            path=_PWA_STATIC_DIR / "manifest.webmanifest",
            media_type="application/manifest+json",
        )

    @router.get("/service-worker.js", include_in_schema=False)
    async def get_service_worker() -> FileResponse:
        return _build_file_response(
            path=_PWA_STATIC_DIR / "service-worker.js",
            media_type="text/javascript",
        )

    @router.get("/pwa/icons/{icon_name}", include_in_schema=False)
    async def get_icon(icon_name: str) -> FileResponse:
        icon_path = _resolve_icon_path(icon_name)
        if icon_path is None:
            raise HTTPException(status_code=404, detail="icon not found")
        return _build_file_response(path=icon_path, media_type="image/png")

    return router


def _build_file_response(*, path: Path, media_type: str) -> FileResponse:
    """Build a file response when the target asset exists."""

    if not path.is_file():
        raise HTTPException(status_code=404, detail="asset not found")
    return FileResponse(path=path, media_type=media_type)


def _resolve_icon_path(icon_name: str) -> Path | None:
    """Resolve icon path while blocking traversal and invalid filenames."""

    if not icon_name:
        return None
    normalized_name = PurePath(icon_name).name
    if normalized_name != icon_name:
        return None
    if not normalized_name.endswith(".png"):
        return None

    candidate = (_ICONS_DIR / normalized_name).resolve()
    if not candidate.is_relative_to(_ICONS_DIR.resolve()):
        return None
    if not candidate.is_file():
        return None
    return candidate
