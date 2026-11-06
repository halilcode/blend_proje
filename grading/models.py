"""
Assessments and grades for a course offering, and how each assessment feeds
the course's learning outcomes.

    CourseOffering ──< Assessment ──< AssessmentMapping >── LearningOutcome
          │               │
          └─< Enrollment ─┴─< Grade
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Assessment(models.Model):
    """A graded component of an offering: midterm, project, quiz, …"""

    class Kind(models.TextChoices):
        MIDTERM = "midterm", "Ara Sınav"
        FINAL = "final", "Final"
        PROJECT = "project", "Proje"
        QUIZ = "quiz", "Kısa Sınav"
        HOMEWORK = "homework", "Ödev"
        LAB = "lab", "Laboratuvar"
        OTHER = "other", "Diğer"

    offering = models.ForeignKey(
        "academics.CourseOffering", on_delete=models.CASCADE, related_name="assessments"
    )
    name = models.CharField(max_length=100)  # e.g. "Midterm 1"
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    max_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("100"),
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    date = models.DateField(null=True, blank=True)
    learning_outcomes = models.ManyToManyField(
        "academics.LearningOutcome",
        through="AssessmentMapping",
        related_name="assessments",
        blank=True,
    )

    class Meta:
        ordering = ["offering", "date", "name"]
        constraints = [
            models.UniqueConstraint(fields=["offering", "name"], name="unique_assessment_name"),
        ]

    def __str__(self):
        return f"{self.offering.course.code} · {self.name}"


class AssessmentMapping(models.Model):
    """
    Weight (in percent) with which an assessment feeds a learning outcome.

    An LO score is the weighted average of the assessment scores that feed it:
        LO = Σ(weight × assessment score) ÷ Σ weights
    """

    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="lo_mappings")
    learning_outcome = models.ForeignKey(
        "academics.LearningOutcome", on_delete=models.CASCADE, related_name="assessment_mappings"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("100"))],
        help_text="Yüzde olarak ağırlık (ör. 60 = %60)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["assessment", "learning_outcome"], name="unique_assessment_lo_mapping"
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gt=0, weight__lte=100),
                name="assessment_lo_weight_0_to_100",
            ),
        ]

    def clean(self):
        # The LO must belong to the same course the assessment is given in.
        if (
            self.assessment_id
            and self.learning_outcome_id
            and self.learning_outcome.course_id != self.assessment.offering.course_id
        ):
            raise ValidationError("Öğrenme çıktısı, değerlendirmenin ait olduğu derse ait olmalı.")

    def __str__(self):
        return f"{self.assessment.name} → {self.learning_outcome.code} (%{self.weight})"


class Enrollment(models.Model):
    """A student taking a course offering."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "student"},
    )
    offering = models.ForeignKey(
        "academics.CourseOffering", on_delete=models.CASCADE, related_name="enrollments"
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["offering", "student"]
        constraints = [
            models.UniqueConstraint(fields=["student", "offering"], name="unique_enrollment"),
        ]

    def __str__(self):
        return f"{self.student} · {self.offering}"


class Grade(models.Model):
    """A student's raw score on one assessment."""

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="grades")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="grades")
    score = models.DecimalField(
        max_digits=6, decimal_places=2, validators=[MinValueValidator(Decimal("0"))]
    )
    entered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entered_grades",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["enrollment", "assessment"], name="unique_grade"),
            models.CheckConstraint(condition=models.Q(score__gte=0), name="grade_score_non_negative"),
        ]

    def clean(self):
        errors = {}
        if self.assessment_id and self.score is not None and self.score > self.assessment.max_score:
            errors["score"] = f"Not, en yüksek puanı ({self.assessment.max_score}) aşamaz."
        if (
            self.assessment_id
            and self.enrollment_id
            and self.assessment.offering_id != self.enrollment.offering_id
        ):
            errors["assessment"] = "Değerlendirme, öğrencinin kayıtlı olduğu şubeye ait olmalı."
        if errors:
            raise ValidationError(errors)

    @property
    def percentage(self):
        """Score normalised to 0–100 so assessments with different max scores can be combined."""
        return self.score * Decimal("100") / self.assessment.max_score

    def __str__(self):
        return f"{self.enrollment.student} · {self.assessment.name}: {self.score}"
