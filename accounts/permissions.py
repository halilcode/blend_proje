"""
Role-based access control, permission definitions, and admin mixins.

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
from django.db import DatabaseError, models

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
    Sync Django Groups based on user.role.
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


def get_field_value(obj, field_path):
    """Traverse relation chain, e.g. 'offering__course__department'."""
    parts = field_path.split("__")
    cur = obj
    for part in parts:
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


def check_instructor_access(obj, instructor_field, user):
    """Check whether the given instructor user is linked via instructor_field."""
    if not obj or not instructor_field or not user:
        return False
    parts = instructor_field.split("__")
    cur = obj
    for i, part in enumerate(parts):
        if hasattr(cur, "filter"):
            sub_path = "__".join(parts[i:])
            return cur.filter(**{sub_path: user}).exists()
        val = getattr(cur, part, None)
        if val is None:
            return False
        cur = val
    if hasattr(cur, "filter"):
        return cur.filter(id=user.id).exists()
    return cur == user


class RoleScopedAdminMixin:
    """
    ModelAdmin mixin providing query filtering and permission enforcement by role:
    - Superusers / Admins: full access.
    - Department Heads: filtered to their department; permissions controlled by
      dept_head_can_add/change/delete flags.
    - Instructors: filtered to offerings they teach; permissions controlled by
      instructor_can_add/change/delete flags.
    """

    dept_field = None          # e.g. "department", "course__department"
    instructor_field = None    # e.g. "instructors", "offering__instructors"

    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False

    instructor_can_view = True
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or user.role == ROLE_ADMIN:
            return qs

        if user.role == ROLE_DEPARTMENT_HEAD:
            if not self.dept_head_can_view or not user.department_id:
                return qs.none()
            if self.dept_field:
                return qs.filter(**{self.dept_field: user.department}).distinct()
            return qs

        if user.role == ROLE_INSTRUCTOR:
            if not self.instructor_can_view or not self.instructor_field:
                return qs.none()
            return qs.filter(**{self.instructor_field: user}).distinct()

        # Students and other roles
        return qs.none()

    def has_view_permission(self, request, obj=None):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True

        if user.role == ROLE_DEPARTMENT_HEAD:
            if not self.dept_head_can_view or not user.department_id:
                return False
            if obj is not None and self.dept_field:
                return get_field_value(obj, self.dept_field) == user.department
            return super().has_view_permission(request, obj)

        if user.role == ROLE_INSTRUCTOR:
            if not self.instructor_can_view or not self.instructor_field:
                return False
            if obj is not None:
                return check_instructor_access(obj, self.instructor_field, user)
            return super().has_view_permission(request, obj)

        return False

    def has_add_permission(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True

        if user.role == ROLE_DEPARTMENT_HEAD:
            return bool(self.dept_head_can_add and user.department_id and super().has_add_permission(request))

        if user.role == ROLE_INSTRUCTOR:
            return bool(self.instructor_can_add and super().has_add_permission(request))

        return False

    def has_change_permission(self, request, obj=None):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True

        if user.role == ROLE_DEPARTMENT_HEAD:
            if not self.dept_head_can_change or not user.department_id:
                return False
            if not super().has_change_permission(request, obj):
                return False
            if obj is not None and self.dept_field:
                return get_field_value(obj, self.dept_field) == user.department
            return True

        if user.role == ROLE_INSTRUCTOR:
            if not self.instructor_can_change:
                return False
            if not super().has_change_permission(request, obj):
                return False
            if obj is not None:
                if not self.instructor_field:
                    return False
                return check_instructor_access(obj, self.instructor_field, user)
            return True

        return False

    def has_delete_permission(self, request, obj=None):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True

        if user.role == ROLE_DEPARTMENT_HEAD:
            if not self.dept_head_can_delete or not user.department_id:
                return False
            if not super().has_delete_permission(request, obj):
                return False
            if obj is not None and self.dept_field:
                return get_field_value(obj, self.dept_field) == user.department
            return True

        if user.role == ROLE_INSTRUCTOR:
            if not self.instructor_can_delete:
                return False
            if not super().has_delete_permission(request, obj):
                return False
            if obj is not None:
                if not self.instructor_field:
                    return False
                return check_instructor_access(obj, self.instructor_field, user)
            return True

        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if user.is_authenticated and not user.is_superuser and user.role != ROLE_ADMIN:
            if user.role == ROLE_DEPARTMENT_HEAD and user.department_id:
                dept = user.department
                if db_field.name == "department":
                    kwargs["queryset"] = db_field.related_model.objects.filter(id=dept.id)
                elif db_field.name == "course":
                    kwargs["queryset"] = db_field.related_model.objects.filter(department=dept)
                elif db_field.name == "offering":
                    kwargs["queryset"] = db_field.related_model.objects.filter(course__department=dept)
                elif db_field.name == "program_outcome":
                    kwargs["queryset"] = db_field.related_model.objects.filter(department=dept)
                elif db_field.name == "learning_outcome":
                    kwargs["queryset"] = db_field.related_model.objects.filter(course__department=dept)
                elif db_field.name == "assessment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__course__department=dept)
                elif db_field.name == "enrollment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__course__department=dept)

            elif user.role == ROLE_INSTRUCTOR:
                if db_field.name == "offering":
                    kwargs["queryset"] = db_field.related_model.objects.filter(instructors=user)
                elif db_field.name == "course":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offerings__instructors=user).distinct()
                elif db_field.name == "assessment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__instructors=user)
                elif db_field.name == "enrollment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__instructors=user)
                elif db_field.name == "learning_outcome":
                    kwargs["queryset"] = db_field.related_model.objects.filter(course__offerings__instructors=user).distinct()
                elif db_field.name == "program_outcome":
                    if user.department_id:
                        kwargs["queryset"] = db_field.related_model.objects.filter(department=user.department)
                elif db_field.name == "student":
                    kwargs["queryset"] = db_field.related_model.objects.filter(role=ROLE_STUDENT)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class RoleScopedInlineMixin:
    """Inline mixin to enforce permission constraints and foreign key filtering."""

    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False

    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False

    def has_add_permission(self, request, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True
        if user.role == ROLE_DEPARTMENT_HEAD:
            return self.dept_head_can_add
        if user.role == ROLE_INSTRUCTOR:
            return self.instructor_can_add
        return False

    def has_change_permission(self, request, obj=None):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True
        if user.role == ROLE_DEPARTMENT_HEAD:
            return self.dept_head_can_change
        if user.role == ROLE_INSTRUCTOR:
            return self.instructor_can_change
        return False

    def has_delete_permission(self, request, obj=None):
        user = request.user
        if not user.is_authenticated:
            return False
        if user.is_superuser or user.role == ROLE_ADMIN:
            return True
        if user.role == ROLE_DEPARTMENT_HEAD:
            return self.dept_head_can_delete
        if user.role == ROLE_INSTRUCTOR:
            return self.instructor_can_delete
        return False

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user
        if user.is_authenticated and not user.is_superuser and user.role != ROLE_ADMIN:
            if user.role == ROLE_DEPARTMENT_HEAD and user.department_id:
                dept = user.department
                if db_field.name == "department":
                    kwargs["queryset"] = db_field.related_model.objects.filter(id=dept.id)
                elif db_field.name == "course":
                    kwargs["queryset"] = db_field.related_model.objects.filter(department=dept)
                elif db_field.name == "offering":
                    kwargs["queryset"] = db_field.related_model.objects.filter(course__department=dept)
                elif db_field.name == "program_outcome":
                    kwargs["queryset"] = db_field.related_model.objects.filter(department=dept)
                elif db_field.name == "learning_outcome":
                    kwargs["queryset"] = db_field.related_model.objects.filter(course__department=dept)
                elif db_field.name == "assessment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__course__department=dept)
                elif db_field.name == "enrollment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__course__department=dept)

            elif user.role == ROLE_INSTRUCTOR:
                if db_field.name == "offering":
                    kwargs["queryset"] = db_field.related_model.objects.filter(instructors=user)
                elif db_field.name == "course":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offerings__instructors=user).distinct()
                elif db_field.name == "assessment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__instructors=user)
                elif db_field.name == "enrollment":
                    kwargs["queryset"] = db_field.related_model.objects.filter(offering__instructors=user)
                elif db_field.name == "learning_outcome":
                    kwargs["queryset"] = db_field.related_model.objects.filter(course__offerings__instructors=user).distinct()
                elif db_field.name == "program_outcome":
                    if user.department_id:
                        kwargs["queryset"] = db_field.related_model.objects.filter(department=user.department)
                elif db_field.name == "student":
                    kwargs["queryset"] = db_field.related_model.objects.filter(role=ROLE_STUDENT)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
