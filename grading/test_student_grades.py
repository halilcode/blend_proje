from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class StudentGradesOnHomeTests(TestCase):
    """Students see their own grades and LO scores per course on the home page."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def home_as(self, username):
        self.client.login(username=username, password="demo12345")
        return self.client.get(reverse("home"))

    def course(self, response, code):
        return next(c for c in response.context["course_details"] if c["course"].code == code)

    def assessment_row(self, course, name):
        return next(r for r in course["assessments"] if r["assessment"].name == name)

    def test_student_sees_all_enrolled_courses(self):
        response = self.home_as("elif")
        codes = [c["course"].code for c in response.context["course_details"]]
        self.assertEqual(codes, ["CSE 311", "CSE 321", "MAT 241"])
        self.assertContains(response, "Derslerim ve notlarım")

    def test_grades_and_lo_scores_match_the_brief_example(self):
        cse311 = self.course(self.home_as("elif"), "CSE 311")
        self.assertEqual(self.assessment_row(cse311, "Midterm")["score"], Decimal("90"))
        self.assertEqual(self.assessment_row(cse311, "Project")["score"], Decimal("80"))
        lo_scores = {row["outcome"].number: row["score"] for row in cse311["learning_outcomes"]}
        self.assertEqual(lo_scores, {1: Decimal("86.0"), 2: Decimal("82.9")})

    def test_grade_out_of_a_smaller_max_score_shows_percentage(self):
        response = self.home_as("elif")
        quiz = self.assessment_row(self.course(response, "CSE 321"), "Quiz 1")
        self.assertEqual(quiz["score"], Decimal("17"))
        self.assertEqual(quiz["percentage"], Decimal("85.0"))
        self.assertContains(response, "17 / 20")

    def test_missing_grade_is_shown_as_pending_not_zero(self):
        response = self.home_as("deniz")
        cse321 = self.course(response, "CSE 321")
        self.assertIsNone(self.assessment_row(cse321, "Quiz 1")["score"])
        self.assertEqual(cse321["graded_count"], 2)
        self.assertContains(response, "Henüz girilmedi")
        self.assertContains(response, "2/3 not girildi")

    def test_student_only_sees_own_grades(self):
        response = self.home_as("mert")
        codes = [c["course"].code for c in response.context["course_details"]]
        self.assertEqual(codes, ["CSE 311", "MAT 241"])
        for name in ("Elif Demir", "Can Yılmaz", "Deniz Kaya"):
            self.assertNotContains(response, name)

    def test_staff_home_has_no_student_grades_section(self):
        response = self.home_as("hoca")
        self.assertNotIn("course_details", response.context)
        self.assertNotContains(response, "Derslerim ve notlarım")
