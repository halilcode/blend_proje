"""
Load demo data: the CSE department's 11 program outcomes, the CSE 311 example
from the project brief, and one user per role.

    python manage.py seed_demo

Safe to run more than once. All demo accounts use the password "demo12345";
never run this against a production database.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

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
from grading.models import Assessment, AssessmentMapping, Enrollment, Grade

DEMO_PASSWORD = "demo12345"

# Short names from the project guidelines. Official wording:
# obs.acibadem.edu.tr/oibs/bologna/progLearnOutcomes.aspx
PROGRAM_OUTCOMES = [
    "Math, science & engineering knowledge",
    "Identify, formulate & solve engineering problems",
    "Design systems under realistic constraints",
    "Use modern techniques, tools & IT",
    "Design & run experiments, analyze data",
    "Work in teams and individually",
    "Communicate verbally & in writing",
    "Lifelong learning",
    "Ethics & professional responsibility",
    "Project, risk & change management; entrepreneurship",
    "Health, safety, environment & legal effects",
]


class Command(BaseCommand):
    help = "Load demo data (11 POs, the CSE 311 example from the brief, one user per role)."

    @transaction.atomic
    def handle(self, *args, **options):
        dept, _ = Department.objects.get_or_create(
            code="CSE", defaults={"name": "Computer Science and Engineering"}
        )
        pos = {}
        for number, short_name in enumerate(PROGRAM_OUTCOMES, start=1):
            pos[number], _ = ProgramOutcome.objects.update_or_create(
                department=dept, number=number, defaults={"short_name": short_name}
            )

        admin = self._user("admin", "Admin", "", User.Role.ADMIN, dept, is_staff=True, is_superuser=True)
        head = self._user("bolum_baskani", "Bölüm", "Başkanı", User.Role.DEPARTMENT_HEAD, dept, is_staff=True)
        instructor = self._user("hoca", "Ahmet", "Hoca", User.Role.INSTRUCTOR, dept, is_staff=True)
        elif_ = self._user("elif", "Elif", "Demir", User.Role.STUDENT, dept, student_number="2021001")
        dept.head = head
        dept.save()

        course, _ = Course.objects.get_or_create(
            code="CSE 311", defaults={"department": dept, "name": "Software Engineering"}
        )
        offering, _ = CourseOffering.objects.get_or_create(
            course=course, year=2026, semester=CourseOffering.Semester.FALL, section=1
        )
        offering.instructors.add(instructor)

        lo1, _ = LearningOutcome.objects.get_or_create(
            course=course, number=1,
            defaults={"description": "Breaks a software problem into parts and integrates the solutions."},
        )
        lo2, _ = LearningOutcome.objects.get_or_create(
            course=course, number=2,
            defaults={"description": "Presents and defends design decisions to a team."},
        )
        for lo, po, weight in [(lo1, pos[1], 100), (lo2, pos[1], 50), (lo2, pos[2], 100)]:
            LearningOutcomeMapping.objects.update_or_create(
                learning_outcome=lo, program_outcome=po, defaults={"weight": weight}
            )
        for po, level in [(pos[1], 5), (pos[2], 4)]:
            CourseContribution.objects.update_or_create(
                course=course, program_outcome=po, defaults={"level": level}
            )

        midterm, _ = Assessment.objects.get_or_create(
            offering=offering, name="Midterm", defaults={"kind": Assessment.Kind.MIDTERM}
        )
        project, _ = Assessment.objects.get_or_create(
            offering=offering, name="Project", defaults={"kind": Assessment.Kind.PROJECT}
        )
        for assessment, lo, weight in [(midterm, lo1, 60), (project, lo1, 40), (midterm, lo2, 40), (project, lo2, 100)]:
            AssessmentMapping.objects.update_or_create(
                assessment=assessment, learning_outcome=lo, defaults={"weight": weight}
            )

        enrollment, _ = Enrollment.objects.get_or_create(student=elif_, offering=offering)
        for assessment, score in [(midterm, 90), (project, 80)]:
            Grade.objects.update_or_create(
                enrollment=enrollment, assessment=assessment,
                defaults={"score": score, "entered_by": instructor},
            )

        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded. Users: {admin.username}, {head.username}, "
            f"{instructor.username}, {elif_.username} (password: {DEMO_PASSWORD})"
        ))

    def _user(self, username, first, last, role, dept, student_number=None, **flags):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first,
                "last_name": last,
                "role": role,
                "department": dept,
                "student_number": student_number,
                **flags,
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        return user
