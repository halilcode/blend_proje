from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import User
from academics.models import (
    Course,
    CourseContribution,
    CourseOffering,
    Department,
    LearningOutcome,
    LearningOutcomeMapping,
    ProgramOutcome,
)

from .models import Assessment, AssessmentMapping, Enrollment, Grade
from .scoring import (
    learning_outcome_scores,
    program_outcome_scores,
    round_score,
    student_po_profile,
    weighted_average,
)


class WeightedAverageTests(TestCase):
    def test_empty_returns_none(self):
        self.assertIsNone(weighted_average([]))

    def test_weights_need_not_sum_to_100(self):
        self.assertEqual(weighted_average([(40, 90), (100, 80)]), Decimal(116) / Decimal("1.4"))


class BriefExampleTests(TestCase):
    """The worked example from the project guidelines (slide 6)."""

    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(code="CSE", name="Computer Science and Engineering")
        cls.po1 = ProgramOutcome.objects.create(department=cls.dept, number=1, short_name="PO 1")
        cls.po2 = ProgramOutcome.objects.create(department=cls.dept, number=2, short_name="PO 2")

        cls.course = Course.objects.create(department=cls.dept, code="CSE 311", name="Software")
        cls.offering = CourseOffering.objects.create(course=cls.course, year=2026, semester="fall")

        cls.lo1 = LearningOutcome.objects.create(course=cls.course, number=1, description="LO 1")
        cls.lo2 = LearningOutcome.objects.create(course=cls.course, number=2, description="LO 2")
        LearningOutcomeMapping.objects.create(learning_outcome=cls.lo1, program_outcome=cls.po1, weight=100)
        LearningOutcomeMapping.objects.create(learning_outcome=cls.lo2, program_outcome=cls.po1, weight=50)
        LearningOutcomeMapping.objects.create(learning_outcome=cls.lo2, program_outcome=cls.po2, weight=100)

        cls.midterm = Assessment.objects.create(offering=cls.offering, name="Midterm", kind="midterm")
        cls.project = Assessment.objects.create(offering=cls.offering, name="Project", kind="project")
        AssessmentMapping.objects.create(assessment=cls.midterm, learning_outcome=cls.lo1, weight=60)
        AssessmentMapping.objects.create(assessment=cls.project, learning_outcome=cls.lo1, weight=40)
        AssessmentMapping.objects.create(assessment=cls.midterm, learning_outcome=cls.lo2, weight=40)
        AssessmentMapping.objects.create(assessment=cls.project, learning_outcome=cls.lo2, weight=100)

        cls.elif_ = User.objects.create_user("elif", role=User.Role.STUDENT, student_number="2021001")
        cls.enrollment = Enrollment.objects.create(student=cls.elif_, offering=cls.offering)
        Grade.objects.create(enrollment=cls.enrollment, assessment=cls.midterm, score=90)
        Grade.objects.create(enrollment=cls.enrollment, assessment=cls.project, score=80)

    def test_learning_outcome_scores(self):
        scores = learning_outcome_scores(self.enrollment)
        self.assertEqual(round_score(scores[self.lo1.id]), Decimal("86.0"))
        self.assertEqual(round_score(scores[self.lo2.id]), Decimal("82.9"))

    def test_program_outcome_scores(self):
        scores = program_outcome_scores(self.enrollment)
        self.assertEqual(round_score(scores[self.po1.id]), Decimal("85.0"))
        self.assertEqual(round_score(scores[self.po2.id]), Decimal("82.9"))

    def test_missing_grade_is_skipped_not_zero(self):
        Grade.objects.filter(assessment=self.project).delete()
        scores = learning_outcome_scores(self.enrollment)
        # Only the midterm is graded, so both LOs equal the midterm score.
        self.assertEqual(scores[self.lo1.id], Decimal(90))
        self.assertEqual(scores[self.lo2.id], Decimal(90))

    def test_scores_are_normalised_by_max_score(self):
        self.midterm.max_score = 50
        self.midterm.save()
        Grade.objects.filter(assessment=self.midterm).update(score=45)  # 45/50 = 90%
        scores = learning_outcome_scores(self.enrollment)
        self.assertEqual(round_score(scores[self.lo1.id]), Decimal("86.0"))

    def test_no_grades_gives_empty_profile(self):
        other = User.objects.create_user("can", role=User.Role.STUDENT, student_number="2021002")
        enrollment = Enrollment.objects.create(student=other, offering=self.offering)
        self.assertEqual(program_outcome_scores(enrollment), {})

    def test_profile_combines_courses_with_contribution_levels(self):
        # A second course that only feeds PO 1, scoring 70 there.
        course = Course.objects.create(department=self.dept, code="CSE 321", name="Data Systems")
        offering = CourseOffering.objects.create(course=course, year=2026, semester="fall")
        lo = LearningOutcome.objects.create(course=course, number=1, description="LO 1")
        LearningOutcomeMapping.objects.create(learning_outcome=lo, program_outcome=self.po1, weight=100)
        final = Assessment.objects.create(offering=offering, name="Final", kind="final")
        AssessmentMapping.objects.create(assessment=final, learning_outcome=lo, weight=100)
        enrollment = Enrollment.objects.create(student=self.elif_, offering=offering)
        Grade.objects.create(enrollment=enrollment, assessment=final, score=70)

        # CSE 311 contributes to PO 1 at level 4, CSE 321 at level 1.
        CourseContribution.objects.create(course=self.course, program_outcome=self.po1, level=4)
        CourseContribution.objects.create(course=course, program_outcome=self.po1, level=1)

        profile = student_po_profile(self.elif_)
        cse311_po1 = program_outcome_scores(self.enrollment)[self.po1.id]
        self.assertEqual(profile[self.po1.id], (4 * cse311_po1 + 1 * 70) / 5)
        # PO 2 only comes from CSE 311 (no contribution row → default level).
        self.assertEqual(round_score(profile[self.po2.id]), Decimal("82.9"))


class GradeValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        dept = Department.objects.create(code="CSE", name="CSE")
        course = Course.objects.create(department=dept, code="CSE 311", name="Software")
        cls.offering = CourseOffering.objects.create(course=course, year=2026, semester="fall")
        cls.other_offering = CourseOffering.objects.create(
            course=course, year=2026, semester="fall", section=2
        )
        cls.assessment = Assessment.objects.create(offering=cls.offering, name="Quiz", max_score=20)
        student = User.objects.create_user("s", role=User.Role.STUDENT)
        cls.enrollment = Enrollment.objects.create(student=student, offering=cls.offering)
        cls.other_enrollment = Enrollment.objects.create(student=student, offering=cls.other_offering)

    def test_score_cannot_exceed_max(self):
        grade = Grade(enrollment=self.enrollment, assessment=self.assessment, score=25)
        with self.assertRaises(ValidationError):
            grade.full_clean()

    def test_assessment_must_match_enrollment_offering(self):
        grade = Grade(enrollment=self.other_enrollment, assessment=self.assessment, score=10)
        with self.assertRaises(ValidationError):
            grade.full_clean()


class UserTests(TestCase):
    def test_blank_student_numbers_do_not_collide(self):
        User.objects.create_user("a", role=User.Role.INSTRUCTOR, student_number="")
        User.objects.create_user("b", role=User.Role.INSTRUCTOR, student_number="")
        self.assertEqual(User.objects.filter(student_number__isnull=True).count(), 2)


class StudentPOProfileChartTests(TestCase):
    """Tests for Issue #10: Student PO profile chart rendering and empty states."""

    @classmethod
    def setUpTestData(cls):
        cls.dept = Department.objects.create(code="CSE", name="Computer Science")
        cls.po1 = ProgramOutcome.objects.create(department=cls.dept, number=1, short_name="Math & Science")
        cls.po2 = ProgramOutcome.objects.create(department=cls.dept, number=2, short_name="Problem Solving")
        cls.po3 = ProgramOutcome.objects.create(department=cls.dept, number=3, short_name="System Design")

        cls.course = Course.objects.create(department=cls.dept, code="CSE 311", name="Software")
        cls.offering = CourseOffering.objects.create(course=cls.course, year=2026, semester="fall")

        cls.lo1 = LearningOutcome.objects.create(course=cls.course, number=1, description="LO 1")
        LearningOutcomeMapping.objects.create(learning_outcome=cls.lo1, program_outcome=cls.po1, weight=100)

        cls.midterm = Assessment.objects.create(offering=cls.offering, name="Midterm", kind="midterm")
        AssessmentMapping.objects.create(assessment=cls.midterm, learning_outcome=cls.lo1, weight=100)

        cls.student = User.objects.create_user(
            "student_chart", password="password", role=User.Role.STUDENT, department=cls.dept
        )
        cls.enrollment = Enrollment.objects.create(student=cls.student, offering=cls.offering)
        # Grade only feeds po1 (score 90). po2 and po3 have no grades.
        Grade.objects.create(enrollment=cls.enrollment, assessment=cls.midterm, score=90)

    def test_chart_renders_rated_and_unrated_program_outcomes(self):
        self.client.login(username="student_chart", password="password")
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

        # Chart container and mobile scroll wrapper must be present
        self.assertContains(resp, "PO profilin")
        self.assertContains(resp, "bar-chart")
        self.assertContains(resp, "chart-scroll-wrapper")

        # PO 1 has score 90.0
        self.assertContains(resp, "style=\"height: 90.0%;\"")

        # Acceptance criterion: Puanı olmayan PO boş görünüyor, 0 değil
        self.assertContains(resp, "bar-empty")
        # Ensure that unrated POs (PO 2 and PO 3) do not display "0.0" as score
        content = resp.content.decode("utf-8")
        self.assertNotIn("style=\"height: 0.0%;\"", content)
        self.assertNotIn("style=\"height: 0%;\"", content)
        # Empty marker must be present
        self.assertContains(resp, "bar-value empty")

    def test_mobile_viewport_and_scrollable_container_present(self):
        self.client.login(username="student_chart", password="password")
        resp = self.client.get("/")
        self.assertContains(resp, "name=\"viewport\"")
        self.assertContains(resp, "chart-scroll-wrapper")


    def test_bar_value_label_sits_on_top_of_its_bar(self):
        self.client.login(username="student_chart", password="password")
        resp = self.client.get("/")
        # The value label is positioned at the bar's height, inside the same
        # fixed-height plot track, so it always sits right above the bar.
        self.assertContains(resp, 'class="bar-value" style="bottom: 90.0%;"')
        self.assertContains(resp, 'class="bar-track"', count=3)

    def test_axis_shows_full_zero_to_hundred_scale(self):
        self.client.login(username="student_chart", password="password")
        resp = self.client.get("/")
        for tick in ("100", "75", "50", "25", "0"):
            self.assertContains(resp, f'<span class="y-axis-label" style="bottom: {tick}%;">{tick}</span>', html=False)

    def test_each_column_has_tooltip_with_po_details(self):
        self.client.login(username="student_chart", password="password")
        resp = self.client.get("/")
        content = resp.content.decode("utf-8")
        self.assertEqual(content.count('role="tooltip"'), 3)
        self.assertEqual(content.count('tabindex="0"'), 3)
        self.assertContains(resp, "Math &amp; Science")
        self.assertContains(resp, "Puan: 90,0 / 100")
        self.assertContains(resp, "Henüz puan yok", count=4)  # 2 tooltips + 2 aria-labels
