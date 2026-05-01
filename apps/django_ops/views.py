"""Views for the django_ops operations web application.

Provides login/logout authentication, role-based redirect after login,
and minimal placeholder landing pages for each operational role.
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET

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


@require_GET  # type: ignore[untyped-decorator]
def logout_view(request: HttpRequest) -> HttpResponse:
    """Log out the current user and redirect to the login page.

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

    Args:
        request: The HTTP request.
        role_label: The display label for the role.

    Returns:
        An HTML response with the placeholder content.
    """
    return render(
        request,
        "django_ops/role_home.html",
        {"role_label": role_label},
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


def smoke(request: HttpRequest) -> HttpResponse:
    """Health/smoke endpoint to validate Django app is running.

    Returns a JSON response with status ``ok`` so monitoring and
    deployment checks can confirm the app is healthy.
    """
    from django.http import JsonResponse

    return JsonResponse({"status": "ok"})
