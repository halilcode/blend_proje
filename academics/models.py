"""
Curriculum structure: departments, program outcomes, courses and their learning
outcomes, and how those learning outcomes map onto program outcomes.

    Course ──< LearningOutcome ──< LearningOutcomeMapping >── ProgramOutcome
       │                                                          ▲
       └──────────────< CourseContribution (1–5) >────────────────┘
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Department(models.Model):
    code = models.CharField(max_length=10, unique=True)  # e.g. "CSE"
    name = models.CharField(max_length=200)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class ProgramOutcome(models.Model):
    """A department-wide outcome (PO 1 … PO 11) every graduate should achieve."""

    department = models.ForeignKey(
        Department, on_delete=models.CASCADE, related_name="program_outcomes"
    )
    number = models.PositiveSmallIntegerField()
    short_name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["department", "number"]
        constraints = [
            models.UniqueConstraint(fields=["department", "number"], name="unique_po_number"),
        ]

    def __str__(self):
        return f"PO {self.number} – {self.short_name}"

    @property
    def code(self):
        return f"PO{self.number}"


class Course(models.Model):
    """A catalogue course (e.g. CSE 311). Its syllabus defines its learning outcomes."""

    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="courses")
    code = models.CharField(max_length=20, unique=True)  # e.g. "CSE 311"
    name = models.CharField(max_length=200)
    credits = models.PositiveSmallIntegerField(default=3)
    ects = models.PositiveSmallIntegerField(default=5)
    description = models.TextField(blank=True)
    program_outcomes = models.ManyToManyField(
        ProgramOutcome,
        through="CourseContribution",
        related_name="courses",
        blank=True,
    )

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} – {self.name}"


class CourseContribution(models.Model):
    """
    How strongly a course contributes to a program outcome, on a 1–5 scale.

    Used when combining one student's per-course PO scores into a single
    department-wide PO profile.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="contributions")
    program_outcome = models.ForeignKey(
        ProgramOutcome, on_delete=models.CASCADE, related_name="contributions"
    )
    level = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Katkı düzeyi (1 = çok düşük, 5 = çok yüksek)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "program_outcome"], name="unique_course_po_contribution"
            ),
            models.CheckConstraint(
                condition=models.Q(level__gte=1, level__lte=5),
                name="contribution_level_1_to_5",
            ),
        ]

    def __str__(self):
        return f"{self.course.code} → {self.program_outcome.code} ({self.level}/5)"


class CourseOffering(models.Model):
    """One run of a course in a given term, taught by one or more instructors."""

    class Semester(models.TextChoices):
        FALL = "fall", "Güz"
        SPRING = "spring", "Bahar"
        SUMMER = "summer", "Yaz"

    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="offerings")
    year = models.PositiveSmallIntegerField()
    semester = models.CharField(max_length=10, choices=Semester.choices)
    section = models.PositiveSmallIntegerField(default=1)
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="taught_offerings",
        blank=True,
        limit_choices_to={"role": "instructor"},
    )

    class Meta:
        ordering = ["-year", "semester", "course__code", "section"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "year", "semester", "section"], name="unique_offering"
            ),
        ]

    def __str__(self):
        return f"{self.course.code} · {self.year} {self.get_semester_display()} · Şube {self.section}"


class LearningOutcome(models.Model):
    """A course-level outcome taken from the course syllabus."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="learning_outcomes")
    number = models.PositiveSmallIntegerField()
    description = models.TextField()
    program_outcomes = models.ManyToManyField(
        ProgramOutcome,
        through="LearningOutcomeMapping",
        related_name="learning_outcomes",
        blank=True,
    )

    class Meta:
        ordering = ["course", "number"]
        constraints = [
            models.UniqueConstraint(fields=["course", "number"], name="unique_lo_number"),
        ]

    def __str__(self):
        return f"{self.course.code} LO {self.number}"

    @property
    def code(self):
        return f"LO{self.number}"


class LearningOutcomeMapping(models.Model):
    """
    Weight (in percent) with which a learning outcome feeds a program outcome.

    A PO score inside a course is the weighted average of its LO scores:
        PO = Σ(weight × LO score) ÷ Σ weights
    """

    learning_outcome = models.ForeignKey(
        LearningOutcome, on_delete=models.CASCADE, related_name="po_mappings"
    )
    program_outcome = models.ForeignKey(
        ProgramOutcome, on_delete=models.CASCADE, related_name="lo_mappings"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(Decimal("100"))],
        help_text="Yüzde olarak ağırlık (ör. 50 = %50)",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["learning_outcome", "program_outcome"], name="unique_lo_po_mapping"
            ),
            models.CheckConstraint(
                condition=models.Q(weight__gt=0, weight__lte=100),
                name="lo_po_weight_0_to_100",
            ),
        ]

    def __str__(self):
        return f"{self.learning_outcome} → {self.program_outcome.code} (%{self.weight})"
