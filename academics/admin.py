from django.contrib import admin

from accounts.permissions import (
    ROLE_INSTRUCTOR,
    RoleScopedAdminMixin,
    RoleScopedInlineMixin,
)
from .models import (
    Course,
    CourseContribution,
    CourseOffering,
    Department,
    LearningOutcome,
    LearningOutcomeMapping,
    ProgramOutcome,
)


class ProgramOutcomeInline(RoleScopedInlineMixin, admin.TabularInline):
    model = ProgramOutcome
    extra = 0
    dept_head_can_add = True
    dept_head_can_change = True
    dept_head_can_delete = True
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False


@admin.register(Department)
class DepartmentAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("code", "name", "head")
    search_fields = ("code", "name")
    inlines = [ProgramOutcomeInline]

    dept_field = "id"
    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_view = False


@admin.register(ProgramOutcome)
class ProgramOutcomeAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("code", "short_name", "department")
    list_filter = (("department", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("short_name", "description")

    dept_field = "department"
    dept_head_can_view = True
    dept_head_can_add = True
    dept_head_can_change = True
    dept_head_can_delete = True
    instructor_can_view = True
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if user.is_authenticated and user.role == ROLE_INSTRUCTOR:
            if user.department_id:
                return qs.filter(department=user.department)
            return qs.filter(courses__offerings__instructors=user).distinct()
        return qs

    def has_view_permission(self, request, obj=None):
        user = request.user
        if user.is_authenticated and user.role == ROLE_INSTRUCTOR:
            if obj is not None and user.department_id:
                return obj.department_id == user.department_id
            return True
        return super().has_view_permission(request, obj)


class LearningOutcomeInline(RoleScopedInlineMixin, admin.TabularInline):
    model = LearningOutcome
    extra = 0
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True


class CourseContributionInline(RoleScopedInlineMixin, admin.TabularInline):
    model = CourseContribution
    extra = 0
    dept_head_can_add = True
    dept_head_can_change = True
    dept_head_can_delete = True
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False


@admin.register(Course)
class CourseAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("code", "name", "department", "credits", "ects")
    list_filter = (("department", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("code", "name")
    inlines = [LearningOutcomeInline, CourseContributionInline]

    dept_field = "department"
    instructor_field = "offerings__instructors"
    dept_head_can_view = True
    dept_head_can_add = True
    dept_head_can_change = True
    dept_head_can_delete = True
    instructor_can_view = True
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False


@admin.register(CourseContribution)
class CourseContributionAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("course", "program_outcome", "level")
    list_filter = (("course__department", admin.RelatedOnlyFieldListFilter), "level")
    search_fields = ("course__code", "course__name", "program_outcome__short_name")

    dept_field = "course__department"
    instructor_field = None
    dept_head_can_view = True
    dept_head_can_add = True
    dept_head_can_change = True
    dept_head_can_delete = True
    instructor_can_view = False
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False


class LearningOutcomeMappingInline(RoleScopedInlineMixin, admin.TabularInline):
    model = LearningOutcomeMapping
    extra = 0
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True


@admin.register(LearningOutcome)
class LearningOutcomeAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("__str__", "course", "description")
    list_filter = (("course", admin.RelatedOnlyFieldListFilter),)
    inlines = [LearningOutcomeMappingInline]

    dept_field = "course__department"
    instructor_field = "course__offerings__instructors"
    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_view = True
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True


@admin.register(CourseOffering)
class CourseOfferingAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("course", "year", "semester", "section")
    list_filter = ("year", "semester", ("course__department", admin.RelatedOnlyFieldListFilter))
    search_fields = ("course__code", "course__name")
    filter_horizontal = ("instructors",)

    dept_field = "course__department"
    instructor_field = "instructors"
    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_view = True
    instructor_can_add = False
    instructor_can_change = False
    instructor_can_delete = False
