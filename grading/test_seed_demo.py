from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase

from accounts.models import User
from academics.models import ProgramOutcome

from .models import Assessment, Enrollment, Grade
from .scoring import round_score, student_po_profile


class SeedDemoTests(TestCase):
    """The demo data used in presentations: stable numbers, safe to re-run."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo", verbosity=0)

    def profile(self, username):
        student = User.objects.get(username=username)
        return {
            po.number: round_score(score)
            for po_id, score in student_po_profile(student).items()
            for po in [ProgramOutcome.objects.get(id=po_id)]
        }

    def test_brief_example_is_unchanged_for_elif(self):
        profile = self.profile("elif")
        self.assertEqual(profile[1], Decimal("85.0"))
        self.assertEqual(profile[2], Decimal("82.9"))

    def test_every_student_has_a_varied_profile_and_some_pos_stay_empty(self):
        for username in ("elif", "can", "deniz", "mert"):
            profile = self.profile(username)
            self.assertGreaterEqual(len(profile), 4, username)
            self.assertFalse({8, 9, 10, 11} & profile.keys(), username)

    def test_ungraded_quiz_is_left_out_not_zero(self):
        deniz = User.objects.get(username="deniz")
        quiz = Assessment.objects.get(offering__course__code="CSE 321", name="Quiz 1")
        self.assertFalse(Grade.objects.filter(enrollment__student=deniz, assessment=quiz).exists())

    def test_running_twice_does_not_duplicate_data(self):
        counts = (Grade.objects.count(), Enrollment.objects.count(), Assessment.objects.count())
        call_command("seed_demo", verbosity=0)
        self.assertEqual(counts, (Grade.objects.count(), Enrollment.objects.count(), Assessment.objects.count()))

    def courses_in_grade_admin(self, username):
        self.client.login(username=username, password="demo12345")
        response = self.client.get("/admin/grading/grade/")
        rows = {g.assessment.offering.course.code for g in response.context["cl"].result_list}
        # Django hides a filter that would offer a single choice, so it may be absent.
        course_filter = next(
            (spec for spec in response.context["cl"].filter_specs
             if spec.field_path == "assessment__offering__course"),
            None,
        )
        choices = course_filter.lookup_choices if course_filter else []
        return rows, {" ".join(label.split(" ")[:2]) for _, label in choices}

    def test_instructors_only_see_their_own_courses_in_admin(self):
        rows, choices = self.courses_in_grade_admin("hoca")
        self.assertEqual(rows, {"CSE 311", "MAT 241"})
        # The sidebar filter must not leak other instructors' course names either.
        self.assertEqual(choices, {"CSE 311", "MAT 241"})

        rows, choices = self.courses_in_grade_admin("hoca2")
        self.assertEqual(rows, {"CSE 321"})
        self.assertLessEqual(choices, {"CSE 321"})

    def test_department_head_sees_all_department_courses(self):
        rows, choices = self.courses_in_grade_admin("bolum_baskani")
        self.assertEqual(rows, {"CSE 311", "CSE 321", "MAT 241"})
        self.assertEqual(choices, {"CSE 311", "CSE 321", "MAT 241"})
