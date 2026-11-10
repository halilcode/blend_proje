from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def csrf_failure(request, reason=""):
    """
    Friendly replacement for Django's CSRF failure page.

    The check itself is unchanged: the rejected request is never processed.
    Typical harmless causes are a form submitted twice (the first submit logs the
    user in and rotates the token) or a form left open in one tab while the user
    logged in/out in another tab.
    """
    # A stale login form re-submitted by someone who is already logged in:
    # the first submit worked, so just take them where the login would have.
    if request.user.is_authenticated and request.path == reverse("login"):
        return redirect("home")

    back_url = request.path
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        back_url = referer

    return render(request, "403_csrf.html", {"back_url": back_url}, status=403)
