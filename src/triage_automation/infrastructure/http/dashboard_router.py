"""FastAPI router for server-rendered monitoring dashboard pages."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def build_dashboard_router() -> APIRouter:
    """Build router exposing Jinja2 server-rendered dashboard pages."""

    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    router = APIRouter(tags=["dashboard"])

    @router.get("/dashboard/cases", response_class=HTMLResponse)
    async def render_case_list_page(request: Request) -> HTMLResponse:
        """Render dashboard list page shell for monitoring cases."""

        return templates.TemplateResponse(
            request=request,
            name="dashboard/cases_list.html",
            context={
                "page_title": "Dashboard de Monitoramento",
            },
        )

    @router.get("/dashboard/cases/{case_id}", response_class=HTMLResponse)
    async def render_case_detail_page(request: Request, case_id: UUID) -> HTMLResponse:
        """Render dashboard detail page shell for one monitoring case."""

        return templates.TemplateResponse(
            request=request,
            name="dashboard/case_detail.html",
            context={
                "page_title": "Detalhe do Caso",
                "case_id": str(case_id),
            },
        )

    return router
