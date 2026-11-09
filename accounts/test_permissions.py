import os
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from academics.models import (
    Course,
    CourseContribution,
    CourseOffering,
    Department,
    LearningOutcome,
    LearningOutcomeMapping,
    ProgramOutcome,
)
from accounts.models import User
from accounts.permissions import GROUP_DEPARTMENT_HEAD, GROUP_INSTRUCTOR, GROUP_ADMIN
from grading.models import Assessment, AssessmentMapping, Enrollment, Grade


class RoleGroupSyncTests(TestCase):
    """Verify that is_staff and group memberships update automatically on role change."""

    def test_createsuperuser_command_creates_working_admin(self):
        with mock.patch.dict(os.environ, {"DJANGO_SUPERUSER_PASSWORD": "Yonetici-12345"}):
            call_command(
                "createsuperuser",
                interactive=False,
                username="yonetici",
                email="yonetici@example.com",
                verbosity=0,
            )
        admin = User.objects.get(username="yonetici")
        self.assertEqual(admin.role, User.Role.ADMIN)
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        client = Client()
        self.assertTrue(client.login(username="yonetici", password="Yonetici-12345"))
        self.assertEqual(client.get(reverse("admin:index")).status_code, 200)

    def test_create_superuser_rejects_non_admin_role(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser("bad", password="pw", role=User.Role.STUDENT)

    def test_student_defaults_to_non_staff_and_no_role_groups(self):
        student = User.objects.create_user("student1", password="pw", role=User.Role.STUDENT)
        self.assertFalse(student.is_staff)
        self.assertFalse(student.is_superuser)
        self.assertFalse(student.groups.exists())

    def test_role_change_from_student_to_instructor_updates_is_staff_and_group(self):
        user = User.objects.create_user("user1", password="pw", role=User.Role.STUDENT)
        self.assertFalse(user.is_staff)

        user.role = User.Role.INSTRUCTOR
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertEqual(list(user.groups.values_list("name", flat=True)), [GROUP_INSTRUCTOR])

    def test_role_change_from_instructor_to_department_head(self):
        user = User.objects.create_user("user2", password="pw", role=User.Role.INSTRUCTOR)
        self.assertTrue(user.is_staff)
        self.assertIn(GROUP_INSTRUCTOR, list(user.groups.values_list("name", flat=True)))

        user.role = User.Role.DEPARTMENT_HEAD
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        group_names = list(user.groups.values_list("name", flat=True))
        self.assertIn(GROUP_DEPARTMENT_HEAD, group_names)
        self.assertNotIn(GROUP_INSTRUCTOR, group_names)

    def test_role_change_from_department_head_to_student_removes_staff_and_group(self):
        user = User.objects.create_user("user3", password="pw", role=User.Role.DEPARTMENT_HEAD)
        self.assertTrue(user.is_staff)
        self.assertIn(GROUP_DEPARTMENT_HEAD, list(user.groups.values_list("name", flat=True)))

        user.role = User.Role.STUDENT
        user.save()
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertFalse(user.groups.filter(name=GROUP_DEPARTMENT_HEAD).exists())


class BasePermissionTestCase(TestCase):
    """Fixture with two departments, courses, offerings, instructors, and students."""

    @classmethod
    def setUpTestData(cls):
        # Departments
        cls.dept_cse = Department.objects.create(code="CSE", name="Computer Science")
        cls.dept_eee = Department.objects.create(code="EEE", name="Electrical Engineering")

        # Users
        cls.admin_user = User.objects.create_user(
            "admin_user", password="password", role=User.Role.ADMIN, is_staff=True, is_superuser=True
        )
        cls.head_cse = User.objects.create_user(
            "head_cse", password="password", role=User.Role.DEPARTMENT_HEAD, department=cls.dept_cse
        )
        cls.dept_cse.head = cls.head_cse
        cls.dept_cse.save()

        cls.head_eee = User.objects.create_user(
            "head_eee", password="password", role=User.Role.DEPARTMENT_HEAD, department=cls.dept_eee
        )
        cls.dept_eee.head = cls.head_eee
        cls.dept_eee.save()

        cls.hoca_a = User.objects.create_user(
            "hoca_a", password="password", role=User.Role.INSTRUCTOR, department=cls.dept_cse
        )
        cls.hoca_b = User.objects.create_user(
            "hoca_b", password="password", role=User.Role.INSTRUCTOR, department=cls.dept_cse
        )

        cls.student_1 = User.objects.create_user(
            "student_1", password="password", role=User.Role.STUDENT, student_number="S001"
        )
        cls.student_2 = User.objects.create_user(
            "student_2", password="password", role=User.Role.STUDENT, student_number="S002"
        )

        # Academics
        cls.po_cse1 = ProgramOutcome.objects.create(
            department=cls.dept_cse, number=1, short_name="CSE PO1"
        )
        cls.po_eee1 = ProgramOutcome.objects.create(
            department=cls.dept_eee, number=1, short_name="EEE PO1"
        )

        cls.course_cse = Course.objects.create(
            department=cls.dept_cse, code="CSE 311", name="Software Engineering"
        )
        cls.course_eee = Course.objects.create(
            department=cls.dept_eee, code="EEE 201", name="Circuit Theory"
        )

        cls.cc_cse = CourseContribution.objects.create(
            course=cls.course_cse, program_outcome=cls.po_cse1, level=4
        )
        cls.cc_eee = CourseContribution.objects.create(
            course=cls.course_eee, program_outcome=cls.po_eee1, level=3
        )

        cls.offering_a = CourseOffering.objects.create(
            course=cls.course_cse, year=2026, semester=CourseOffering.Semester.FALL, section=1
        )
        cls.offering_a.instructors.add(cls.hoca_a)

        cls.offering_b = CourseOffering.objects.create(
            course=cls.course_cse, year=2026, semester=CourseOffering.Semester.FALL, section=2
        )
        cls.offering_b.instructors.add(cls.hoca_b)

        # Assessments
        cls.assess_a = Assessment.objects.create(
            offering=cls.offering_a, name="Midterm A", max_score=Decimal("100")
        )
        cls.assess_b = Assessment.objects.create(
            offering=cls.offering_b, name="Midterm B", max_score=Decimal("100")
        )

        # Enrollments & Grades
        cls.enroll_a = Enrollment.objects.create(student=cls.student_1, offering=cls.offering_a)
        cls.enroll_b = Enrollment.objects.create(student=cls.student_2, offering=cls.offering_b)

        cls.grade_a = Grade.objects.create(
            enrollment=cls.enroll_a, assessment=cls.assess_a, score=Decimal("85"), entered_by=cls.hoca_a
        )
        cls.grade_b = Grade.objects.create(
            enrollment=cls.enroll_b, assessment=cls.assess_b, score=Decimal("70"), entered_by=cls.hoca_b
        )


class StudentPermissionTests(BasePermissionTestCase):
    """Tests confirming student cannot access admin panel and only sees own scores on home."""

    def test_student_cannot_access_admin_panel(self):
        client = Client()
        client.login(username="student_1", password="password")

        resp = client.get("/admin/")
        # Student has is_staff=False, so Django admin redirects to login page with next=/admin/
        self.assertIn(resp.status_code, [302, 403])
        if resp.status_code == 302:
            self.assertIn(reverse("admin:login"), resp.headers.get("Location", ""))

    def test_student_cannot_access_grade_admin_directly(self):
        client = Client()
        client.login(username="student_1", password="password")
        resp = client.get(f"/admin/grading/grade/{self.grade_a.id}/change/")
        self.assertIn(resp.status_code, [302, 403])

    def test_student_sees_only_own_po_profile_on_home(self):
        client = Client()
        client.login(username="student_1", password="password")
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PO profilin")


class InstructorPermissionTests(BasePermissionTestCase):
    """
    Tests confirming:
    - Hoca A cannot view or edit Hoca B's grade, offering, assessment.
    - Hoca A CAN edit their own section's grade.
    - Grade.entered_by is automatically set to the editing instructor.
    """

    def setUp(self):
        self.client_a = Client()
        self.client_a.login(username="hoca_a", password="password")

    def test_instructor_a_cannot_see_instructor_b_grade_in_list(self):
        resp = self.client_a.get("/admin/grading/grade/")
        self.assertEqual(resp.status_code, 200)
        # Should see Section A's student and assessment but not Section B
        self.assertContains(resp, self.student_1.username)
        self.assertContains(resp, "Midterm A")
        self.assertNotContains(resp, self.student_2.username)
        self.assertNotContains(resp, "Midterm B")

    def test_instructor_a_cannot_open_instructor_b_grade_via_url(self):
        # Direct URL access to Hoca B's grade must return 404 or 403
        resp = self.client_a.get(f"/admin/grading/grade/{self.grade_b.id}/change/")
        self.assertIn(resp.status_code, [403, 404])

    def test_instructor_a_cannot_post_edit_instructor_b_grade(self):
        post_data = {
            "enrollment": self.enroll_b.id,
            "assessment": self.assess_b.id,
            "score": "99.00",
        }
        resp = self.client_a.post(f"/admin/grading/grade/{self.grade_b.id}/change/", post_data)
        self.assertIn(resp.status_code, [403, 404])
        self.grade_b.refresh_from_db()
        self.assertEqual(self.grade_b.score, Decimal("70"))

    def test_instructor_a_cannot_delete_instructor_b_grade(self):
        resp = self.client_a.post(
            f"/admin/grading/grade/{self.grade_b.id}/delete/",
            {"post": "yes"},
        )
        self.assertIn(resp.status_code, [403, 404])
        self.assertTrue(Grade.objects.filter(id=self.grade_b.id).exists())

    def test_instructor_a_can_open_and_edit_own_grade(self):
        # Can open own grade change page
        resp = self.client_a.get(f"/admin/grading/grade/{self.grade_a.id}/change/")
        self.assertEqual(resp.status_code, 200)

        # Can submit updated score
        post_data = {
            "enrollment": self.enroll_a.id,
            "assessment": self.assess_a.id,
            "score": "95.00",
        }
        resp = self.client_a.post(f"/admin/grading/grade/{self.grade_a.id}/change/", post_data)
        # Should redirect to list view on successful save
        self.assertIn(resp.status_code, [200, 302])
        self.grade_a.refresh_from_db()
        self.assertEqual(self.grade_a.score, Decimal("95.00"))
        # entered_by is automatically set to hoca_a
        self.assertEqual(self.grade_a.entered_by, self.hoca_a)

    def test_instructor_a_cannot_open_instructor_b_offering(self):
        resp = self.client_a.get(f"/admin/academics/courseoffering/{self.offering_b.id}/change/")
        self.assertIn(resp.status_code, [403, 404])

    def test_instructor_a_cannot_open_instructor_b_assessment(self):
        resp = self.client_a.get(f"/admin/grading/assessment/{self.assess_b.id}/change/")
        self.assertIn(resp.status_code, [403, 404])

    def test_instructor_cannot_access_course_contribution(self):
        resp = self.client_a.get("/admin/academics/coursecontribution/")
        self.assertIn(resp.status_code, [403, 404])


class DepartmentHeadPermissionTests(BasePermissionTestCase):
    """
    Tests confirming:
    - Bölüm başkanı CourseContribution düzenleyebiliyor.
    - Bölüm başkanı kendi bölümünün notlarını görüyor ama not değiştiremiyor / ekleyemiyor.
    """

    def setUp(self):
        self.client_head = Client()
        self.client_head.login(username="head_cse", password="password")

    def test_department_head_can_edit_course_contribution_in_own_department(self):
        resp = self.client_head.get(f"/admin/academics/coursecontribution/{self.cc_cse.id}/change/")
        self.assertEqual(resp.status_code, 200)

        post_data = {
            "course": self.course_cse.id,
            "program_outcome": self.po_cse1.id,
            "level": 5,
        }
        resp = self.client_head.post(f"/admin/academics/coursecontribution/{self.cc_cse.id}/change/", post_data)
        self.assertIn(resp.status_code, [200, 302])
        self.cc_cse.refresh_from_db()
        self.assertEqual(self.cc_cse.level, 5)

    def test_department_head_cannot_edit_other_department_course_contribution(self):
        resp = self.client_head.get(f"/admin/academics/coursecontribution/{self.cc_eee.id}/change/")
        self.assertIn(resp.status_code, [403, 404])

    def test_department_head_can_view_grades_in_own_department(self):
        resp = self.client_head.get("/admin/grading/grade/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, self.student_1.username)
        self.assertContains(resp, self.student_2.username)
        self.assertContains(resp, "Midterm A")
        self.assertContains(resp, "Midterm B")

    def test_department_head_cannot_change_grade(self):
        # Dept head visiting grade change page sees read-only or gets 403 on POST
        post_data = {
            "enrollment": self.enroll_a.id,
            "assessment": self.assess_a.id,
            "score": "50.00",
        }
        resp = self.client_head.post(f"/admin/grading/grade/{self.grade_a.id}/change/", post_data)
        self.assertEqual(resp.status_code, 403)
        self.grade_a.refresh_from_db()
        self.assertEqual(self.grade_a.score, Decimal("85.00"))

    def test_department_head_cannot_add_grade(self):
        resp = self.client_head.get("/admin/grading/grade/add/")
        self.assertEqual(resp.status_code, 403)
