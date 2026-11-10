"""
Load demo data: the CSE department's 11 program outcomes, the CSE 311 example
from the project brief (Elif: PO 1 = 85.0, PO 2 = 82.9), two more courses
(CSE 321, MAT 241), two instructors, a department head and four students.

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
    help = "Load demo data (11 POs, 3 courses, 2 instructors, 4 students; CSE 311 brief example)."

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

        # --- More students, a second instructor and two more courses ---------
        # These courses feed PO 3–7 only, so Elif's PO 1/PO 2 (the brief's worked
        # example above) stay exactly 85.0 / 82.9. PO 8–11 get no data on purpose
        # to show the "no score yet" state.
        instructor2 = self._user("hoca2", "Ayşe", "Hoca", User.Role.INSTRUCTOR, dept, is_staff=True)
        can = self._user("can", "Can", "Yılmaz", User.Role.STUDENT, dept, student_number="2021002")
        deniz = self._user("deniz", "Deniz", "Kaya", User.Role.STUDENT, dept, student_number="2021003")
        mert = self._user("mert", "Mert", "Arslan", User.Role.STUDENT, dept, student_number="2021004")

        for student, scores in [(can, (70, 95)), (deniz, (55, 60)), (mert, (100, 88))]:
            enr, _ = Enrollment.objects.get_or_create(student=student, offering=offering)
            for assessment, score in zip((midterm, project), scores):
                Grade.objects.update_or_create(
                    enrollment=enr, assessment=assessment,
                    defaults={"score": score, "entered_by": instructor},
                )

        self._course(
            dept, pos, instructor2, code="CSE 321", name="Data Systems",
            los=[
                (1, "Designs a normalized relational data model.", [(3, 100), (5, 50)]),
                (2, "Writes queries and transactions that keep data consistent.", [(4, 100)]),
                (3, "Builds and presents a data-driven system as a team.", [(6, 100), (7, 50)]),
            ],
            contributions=[(3, 5), (4, 4), (5, 3), (6, 4), (7, 3)],
            assessments=[
                ("Midterm", Assessment.Kind.MIDTERM, 100, [(1, 60), (2, 50)]),
                ("Project", Assessment.Kind.PROJECT, 100, [(1, 40), (3, 100)]),
                ("Quiz 1", Assessment.Kind.QUIZ, 20, [(2, 50)]),
            ],
            grades=[
                (elif_, {"Midterm": 78, "Project": 92, "Quiz 1": 17}),
                (can, {"Midterm": 88, "Project": 70, "Quiz 1": 12}),
                # Deniz's quiz is not graded yet: it is left out, not counted as 0.
                (deniz, {"Midterm": 64, "Project": 75}),
            ],
        )
        self._course(
            dept, pos, instructor, code="MAT 241", name="Probability and Statistics",
            los=[
                (1, "Models uncertainty with probability distributions.", [(5, 100)]),
                (2, "Draws conclusions from data with statistical inference.", [(5, 50), (4, 50)]),
            ],
            contributions=[(5, 4), (4, 2)],
            assessments=[
                ("Midterm", Assessment.Kind.MIDTERM, 100, [(1, 100)]),
                ("Final", Assessment.Kind.FINAL, 100, [(1, 40), (2, 100)]),
            ],
            grades=[
                (elif_, {"Midterm": 72, "Final": 81}),
                (can, {"Midterm": 95, "Final": 90}),
                (deniz, {"Midterm": 45, "Final": 58}),
                (mert, {"Midterm": 83, "Final": 77}),
            ],
        )

        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded. Users: {admin.username}, {head.username}, "
            f"{instructor.username}, {instructor2.username}, {elif_.username}, "
            f"{can.username}, {deniz.username}, {mert.username} (password: {DEMO_PASSWORD})"
        ))

    def _course(self, dept, pos, instructor, *, code, name, los, contributions, assessments, grades):
        """Create (or update) one course offering with its LOs, weights and grades."""
        course, _ = Course.objects.get_or_create(code=code, defaults={"department": dept, "name": name})
        offering, _ = CourseOffering.objects.get_or_create(
            course=course, year=2026, semester=CourseOffering.Semester.FALL, section=1
        )
        offering.instructors.add(instructor)

        lo_by_number = {}
        for number, description, po_weights in los:
            lo, _ = LearningOutcome.objects.get_or_create(
                course=course, number=number, defaults={"description": description}
            )
            lo_by_number[number] = lo
            for po_number, weight in po_weights:
                LearningOutcomeMapping.objects.update_or_create(
                    learning_outcome=lo, program_outcome=pos[po_number], defaults={"weight": weight}
                )
        for po_number, level in contributions:
            CourseContribution.objects.update_or_create(
                course=course, program_outcome=pos[po_number], defaults={"level": level}
            )

        assessment_by_name = {}
        for a_name, kind, max_score, lo_weights in assessments:
            assessment, _ = Assessment.objects.update_or_create(
                offering=offering, name=a_name, defaults={"kind": kind, "max_score": max_score}
            )
            assessment_by_name[a_name] = assessment
            for lo_number, weight in lo_weights:
                AssessmentMapping.objects.update_or_create(
                    assessment=assessment, learning_outcome=lo_by_number[lo_number],
                    defaults={"weight": weight},
                )

        for student, scores in grades:
            enrollment, _ = Enrollment.objects.get_or_create(student=student, offering=offering)
            for a_name, score in scores.items():
                Grade.objects.update_or_create(
                    enrollment=enrollment, assessment=assessment_by_name[a_name],
                    defaults={"score": score, "entered_by": instructor},
                )

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
