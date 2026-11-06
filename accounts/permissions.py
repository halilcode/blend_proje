"""
Role-based access control and admin mixins.

Roles and their capabilities:
- Admin: Full system access.
- Department Head: Manages POs, Courses, CourseContributions for their department.
  Can view all courses, offerings, assessments, enrollments, and grades within their
  department, but CANNOT add, change, or delete grades or assessments.
- Instructor: Can only see CourseOfferings they teach.
  Can manage Assessments, AssessmentMappings, Enrollments, and Grades for their offerings.
  Can edit LearningOutcomes and LO->PO mappings for courses they teach.
  Cannot view or edit other instructors' offerings, grades, or assessments.
  Grade.entered_by is automatically set to the instructor.
- Student: Cannot log in to the admin site (is_staff=False).
"""

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, models
from django.http import Http404

ROLE_ADMIN = "admin"
ROLE_DEPARTMENT_HEAD = "department_head"
ROLE_INSTRUCTOR = "instructor"
ROLE_STUDENT = "student"

GROUP_ADMIN = "Sistem Yöneticisi"
GROUP_DEPARTMENT_HEAD = "Bölüm Başkanı"
GROUP_INSTRUCTOR = "Öğretim Üyesi"

ROLE_GROUPS = {
    ROLE_ADMIN: GROUP_ADMIN,
    ROLE_DEPARTMENT_HEAD: GROUP_DEPARTMENT_HEAD,
    ROLE_INSTRUCTOR: GROUP_INSTRUCTOR,
}

# (app_label, codename)
DEPARTMENT_HEAD_PERMISSIONS = [
    # Department
    ("academics", "view_department"),
    # ProgramOutcome
    ("academics", "view_programoutcome"),
    ("academics", "add_programoutcome"),
    ("academics", "change_programoutcome"),
    ("academics", "delete_programoutcome"),
    # Course
    ("academics", "view_course"),
    ("academics", "add_course"),
    ("academics", "change_course"),
    ("academics", "delete_course"),
    # CourseContribution
    ("academics", "view_coursecontribution"),
    ("academics", "add_coursecontribution"),
    ("academics", "change_coursecontribution"),
    ("academics", "delete_coursecontribution"),
    # LearningOutcome & Mapping (view only)
    ("academics", "view_learningoutcome"),
    ("academics", "view_learningoutcomemapping"),
    # CourseOffering (view only)
    ("academics", "view_courseoffering"),
    # Grading models (view only)
    ("grading", "view_assessment"),
    ("grading", "view_assessmentmapping"),
    ("grading", "view_enrollment"),
    ("grading", "view_grade"),
]

INSTRUCTOR_PERMISSIONS = [
    # Academics
    ("academics", "view_course"),
    ("academics", "view_courseoffering"),
    ("academics", "view_programoutcome"),
    ("academics", "view_learningoutcome"),
    ("academics", "add_learningoutcome"),
    ("academics", "change_learningoutcome"),
    ("academics", "delete_learningoutcome"),
    ("academics", "view_learningoutcomemapping"),
    ("academics", "add_learningoutcomemapping"),
    ("academics", "change_learningoutcomemapping"),
    ("academics", "delete_learningoutcomemapping"),
    # Grading
    ("grading", "view_assessment"),
    ("grading", "add_assessment"),
    ("grading", "change_assessment"),
    ("grading", "delete_assessment"),
    ("grading", "view_assessmentmapping"),
    ("grading", "add_assessmentmapping"),
    ("grading", "change_assessmentmapping"),
    ("grading", "delete_assessmentmapping"),
    ("grading", "view_enrollment"),
    ("grading", "add_enrollment"),
    ("grading", "change_enrollment"),
    ("grading", "delete_enrollment"),
    ("grading", "view_grade"),
    ("grading", "add_grade"),
    ("grading", "change_grade"),
    ("grading", "delete_grade"),
]

ROLE_PERMISSIONS = {
    GROUP_DEPARTMENT_HEAD: DEPARTMENT_HEAD_PERMISSIONS,
    GROUP_INSTRUCTOR: INSTRUCTOR_PERMISSIONS,
}


def sync_user_groups(user):
    """
    Sync Django Groups and is_staff based on user.role.
    Safe to call during user save or data migrations.
    """
    try:
        target_group_name = ROLE_GROUPS.get(user.role)
        all_group_names = set(ROLE_GROUPS.values())

        current_groups = list(user.groups.filter(name__in=all_group_names))
        to_remove = [g for g in current_groups if g.name != target_group_name]
        if to_remove:
            user.groups.remove(*to_remove)

        if target_group_name:
            group, _ = Group.objects.get_or_create(name=target_group_name)
            if group not in current_groups:
                user.groups.add(group)
    except DatabaseError:
        pass
