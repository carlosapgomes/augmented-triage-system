"""Views for the django_ops operations web application.

Provides login/logout authentication, role-based redirect after login,
minimal placeholder landing pages for each operational role, and PWA
installability assets (manifest and online-only service worker).
"""

from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

# Roles eligible for the installable PWA shell (remote-capable).
PWA_CAPABLE_ROLES: frozenset[str] = frozenset({"doctor", "manager", "admin"})

# Directory containing PWA static assets served directly by Django views.
PWA_STATIC_DIR: Path = Path(__file__).resolve().parent / "static" / "django_ops" / "pwa"

# Map each role value to its landing URL path.
ROLE_HOME_MAP: dict[str, str] = {
    "nir": "/nir/",
    "doctor": "/doctor/",
    "scheduler": "/scheduler/",
    "manager": "/manager/",
    "admin": "/admin/",
}


def _get_role_redirect_url(role: str) -> str:
    """Return the landing URL for the given role.

    Args:
        role: The user's role string value.

    Returns:
        The URL path for the role's landing page, defaults to ``/nir/``.
    """
    return ROLE_HOME_MAP.get(role, "/nir/")


def login_view(request: HttpRequest) -> HttpResponse:
    """Handle login form display and authentication.

    GET: renders the login form with email and password fields.
    POST: authenticates credentials and creates a session, then
    redirects to the role-specific landing page.

    Args:
        request: The HTTP request.

    Returns:
        The login form on GET/failed auth, or a redirect on success.
    """
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            redirect_url = _get_role_redirect_url(str(user.role))
            return HttpResponseRedirect(redirect_url)
        return render(
            request,
            "django_ops/login.html",
            {"error": "Invalid email or password."},
        )

    return render(request, "django_ops/login.html")


@require_POST  # type: ignore[untyped-decorator]
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user via POST and redirect to the login page.

    Args:
        request: The HTTP request.

    Returns:
        A redirect to the login page.
    """
    logout(request)
    return redirect("/login/")


@require_GET  # type: ignore[untyped-decorator]
def root_redirect(request: HttpRequest) -> HttpResponse:
    """Redirect unauthenticated users to login, authenticated to their home.

    Args:
        request: The HTTP request.

    Returns:
        A redirect to login (unauthenticated) or role home (authenticated).
    """
    if request.user.is_authenticated:
        redirect_url = _get_role_redirect_url(str(request.user.role))
        return HttpResponseRedirect(redirect_url)
    return redirect("/login/")


def _role_home(request: HttpRequest, role_label: str) -> HttpResponse:
    """Render a minimal placeholder page for a given role.

    For remote-capable roles (doctor, manager, admin) the response
    includes PWA installability metadata so the page is installable
    as a standalone app on supported mobile browsers.

    Args:
        request: The HTTP request.
        role_label: The display label for the role.

    Returns:
        An HTML response with the placeholder content.
    """
    user_role: str = getattr(request.user, "role", "")
    pwa_capable: bool = user_role in PWA_CAPABLE_ROLES
    return render(
        request,
        "django_ops/role_home.html",
        {
            "role_label": role_label,
            "pwa_capable": pwa_capable,
        },
    )


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def nir_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for NIR users."""
    return _role_home(request, "NIR")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def doctor_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Doctor users."""
    return _role_home(request, "Doctor")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def scheduler_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Scheduler users."""
    return _role_home(request, "Scheduler")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def manager_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Manager users."""
    return _role_home(request, "Manager")


@login_required  # type: ignore[untyped-decorator]
@require_GET  # type: ignore[untyped-decorator]
def admin_home(request: HttpRequest) -> HttpResponse:
    """Placeholder landing page for Admin users."""
    return _role_home(request, "Admin")


@require_GET  # type: ignore[untyped-decorator]
def manifest_view(request: HttpRequest) -> HttpResponse:
    """Serve the PWA web app manifest.

    Returns the manifest.webmanifest file with the correct
    ``application/manifest+json`` content type so browsers
    recognize it as a valid installability document.

    Args:
        request: The HTTP request.

    Returns:
        The manifest file content.
    """
    manifest_path = PWA_STATIC_DIR / "manifest.webmanifest"
    return HttpResponse(
        manifest_path.read_bytes(),
        content_type="application/manifest+json",
    )


@require_GET  # type: ignore[untyped-decorator]
def service_worker_view(request: HttpRequest) -> HttpResponse:
    """Serve the online-only PWA service worker.

    The service worker uses network-only fetch behavior and does
    not cache any clinical content for offline use.

    Args:
        request: The HTTP request.

    Returns:
        The service worker JavaScript content.
    """
    sw_path = PWA_STATIC_DIR / "service-worker.js"
    return HttpResponse(
        sw_path.read_bytes(),
        content_type="text/javascript",
    )


def smoke(request: HttpRequest) -> HttpResponse:
    """Health/smoke endpoint to validate Django app is running.

    Returns a JSON response with status ``ok`` so monitoring and
    deployment checks can confirm the app is healthy.
    """
    from django.http import JsonResponse

    return JsonResponse({"status": "ok"})
