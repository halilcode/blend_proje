from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from academics.models import ProgramOutcome


class SiteLoginTests(TestCase):
    """Users sign in through the site's own login form (not the staff-only admin login)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def login_via_form(self, username, password="demo12345", **extra):
        return self.client.post(
            reverse("login"), {"username": username, "password": password, **extra}
        )

    def test_anonymous_home_links_to_site_login(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertNotContains(response, reverse("admin:login"))

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_student_can_log_in_via_form_and_sees_po_profile(self):
        response = self.login_via_form("elif")
        self.assertRedirects(response, reverse("home"))

        home = self.client.get(reverse("home"))
        self.assertEqual(home.context["user"].username, "elif")
        po1 = ProgramOutcome.objects.get(department__code="CSE", number=1)
        scores = {row["outcome"].id: row["score"] for row in home.context["po_rows"]}
        self.assertEqual(scores[po1.id], Decimal("85.0"))

    def test_wrong_password_shows_error_and_does_not_log_in(self):
        response = self.login_via_form("elif", password="yanlis-parola")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_respects_next_parameter(self):
        response = self.login_via_form("hoca", next=reverse("admin:index"))
        self.assertRedirects(response, reverse("admin:index"))

    def test_staff_user_can_log_in_via_form(self):
        response = self.login_via_form("hoca")
        self.assertRedirects(response, reverse("home"))
        self.assertContains(self.client.get(reverse("home")), reverse("admin:index"))

    def test_logged_in_user_visiting_login_is_redirected_home(self):
        self.login_via_form("elif")
        self.assertRedirects(self.client.get(reverse("login")), reverse("home"))

    def test_logout_via_post_ends_session(self):
        self.login_via_form("elif")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_admin_login_still_rejects_students(self):
        response = self.client.post(
            reverse("admin:login"), {"username": "elif", "password": "demo12345"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class CsrfFailureTests(TestCase):
    """CSRF is still enforced, but failures show a friendly page instead of Django's debug page."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def setUp(self):
        self.client = self.client_class(enforce_csrf_checks=True)

    def token_from(self, response):
        return response.context["csrf_token"]

    def test_double_submitted_login_goes_home_instead_of_error(self):
        first_token = self.token_from(self.client.get(reverse("login")))
        credentials = {"username": "elif", "password": "demo12345", "csrfmiddlewaretoken": first_token}
        self.assertRedirects(self.client.post(reverse("login"), credentials), reverse("home"))
        # Login rotated the token; the same form submitted again carries the old one.
        response = self.client.post(reverse("login"), credentials)
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(self.client.get(reverse("home")).context["user"].username, "elif")

    def test_anonymous_bad_token_shows_friendly_page_and_rejects(self):
        self.client.get(reverse("login"))  # sets the CSRF cookie
        response = self.client.post(
            reverse("login"),
            {"username": "elif", "password": "demo12345", "csrfmiddlewaretoken": "x" * 64},
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Sayfanın süresi doldu", status_code=403)
        self.assertNotContains(response, "CSRF_FAILURE_VIEW", status_code=403)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_back_link_uses_same_site_referer_only(self):
        self.client.get(reverse("login"))
        bad = {"csrfmiddlewaretoken": "x" * 64}
        same = self.client.post(reverse("login"), bad, HTTP_REFERER="http://testserver/giris/?next=/admin/")
        self.assertEqual(same.context["back_url"], "http://testserver/giris/?next=/admin/")
        other = self.client.post(reverse("login"), bad, HTTP_REFERER="https://evil.example.com/")
        self.assertEqual(other.context["back_url"], reverse("home"))
        # No referer: never link back to a POST-only URL (it would answer 405).
        none = self.client.post(reverse("login"), bad)
        self.assertEqual(none.context["back_url"], reverse("home"))

    def test_logged_in_admin_form_with_stale_token_is_rejected_with_friendly_page(self):
        token = self.token_from(self.client.get(reverse("login")))
        self.client.post(reverse("login"), {"username": "hoca", "password": "demo12345", "csrfmiddlewaretoken": token})
        response = self.client.post("/admin/grading/grade/1/change/", {"score": "100", "csrfmiddlewaretoken": token})
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Sayfaya dön", status_code=403)

    def login_via_form(self, username):
        token = self.token_from(self.client.get(reverse("login")))
        return self.client.post(
            reverse("login"),
            {"username": username, "password": "demo12345", "csrfmiddlewaretoken": token},
        )

    def test_logout_via_form_with_valid_token(self):
        self.login_via_form("elif")
        token = self.token_from(self.client.get(reverse("home")))
        response = self.client.post(reverse("logout"), {"csrfmiddlewaretoken": token})
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_with_stale_token_still_logs_out(self):
        self.login_via_form("hoca")
        response = self.client.post(reverse("logout"), {"csrfmiddlewaretoken": "x" * 64})
        self.assertRedirects(response, reverse("home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_csrf_token_lives_in_session_not_in_a_cookie(self):
        # No separate "csrftoken" cookie can go out of sync with the form:
        # the token is stored in the server-side session.
        response = self.client.get(reverse("login"))
        self.assertNotIn("csrftoken", response.cookies)
        self.assertRedirects(self.login_via_form("hoca"), reverse("home"))
        self.assertNotIn("csrftoken", self.client.cookies)
