from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def csrf_failure(request, reason=""):
    """
    Friendly replacement for Django's CSRF failure page.

    The rejected request is never processed. Typical harmless causes are a form
    submitted twice (the first submit logs the user in and rotates the token) or
    a form left open in one tab while the user logged in/out in another tab.
    """
    # A stale login form re-submitted by someone who is already logged in:
    # the first submit worked, so just take them where the login would have.
    if request.user.is_authenticated and request.path == reverse("login"):
        return redirect("home")

    # A logout that fails the CSRF check: ending the session is what the user
    # asked for and cannot leak or change any data, so do it rather than
    # trapping them in a session they are trying to leave.
    if request.path == reverse("logout"):
        logout(request)
        return redirect("home")

    # Send the user back to the page the form was on (same site only). The
    # form's own URL may accept POST only, so never link to it.
    back_url = reverse("home")
    referer = request.META.get("HTTP_REFERER")
    if referer and url_has_allowed_host_and_scheme(
        referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        back_url = referer

    return render(request, "403_csrf.html", {"back_url": back_url}, status=403)
