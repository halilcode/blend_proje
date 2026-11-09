from django.contrib import admin

from accounts.permissions import (
    ROLE_INSTRUCTOR,
    RoleScopedAdminMixin,
    RoleScopedInlineMixin,
)
from .models import Assessment, AssessmentMapping, Enrollment, Grade


class AssessmentMappingInline(RoleScopedInlineMixin, admin.TabularInline):
    model = AssessmentMapping
    extra = 0
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True


@admin.register(Assessment)
class AssessmentAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "kind", "offering", "max_score", "date")
    list_filter = ("kind", "offering__year", "offering__semester", "offering__course")
    search_fields = ("name", "offering__course__code")
    inlines = [AssessmentMappingInline]

    dept_field = "offering__course__department"
    instructor_field = "offering__instructors"
    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_view = True
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True


class GradeInline(RoleScopedInlineMixin, admin.TabularInline):
    model = Grade
    extra = 0
    fields = ("assessment", "score", "entered_by", "updated_at")
    readonly_fields = ("updated_at",)

    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if request.user.is_authenticated and request.user.role == ROLE_INSTRUCTOR:
            if "entered_by" not in fields:
                fields.append("entered_by")
        return fields


@admin.register(Enrollment)
class EnrollmentAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("student", "offering", "enrolled_at")
    list_filter = ("offering__year", "offering__semester", "offering__course")
    search_fields = ("student__username", "student__last_name", "student__student_number")
    inlines = [GradeInline]

    dept_field = "offering__course__department"
    instructor_field = "offering__instructors"
    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_view = True
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Grade):
                if not instance.entered_by_id or request.user.role == ROLE_INSTRUCTOR:
                    instance.entered_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(Grade)
class GradeAdmin(RoleScopedAdminMixin, admin.ModelAdmin):
    list_display = ("enrollment", "assessment", "score", "entered_by", "updated_at")
    list_filter = ("assessment__offering__course", "assessment__kind")
    search_fields = ("enrollment__student__username", "enrollment__student__last_name")
    readonly_fields = ("updated_at",)

    dept_field = "enrollment__offering__course__department"
    instructor_field = "enrollment__offering__instructors"
    dept_head_can_view = True
    dept_head_can_add = False
    dept_head_can_change = False
    dept_head_can_delete = False
    instructor_can_view = True
    instructor_can_add = True
    instructor_can_change = True
    instructor_can_delete = True

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if "updated_at" not in fields:
            fields.append("updated_at")
        if request.user.is_authenticated and request.user.role == ROLE_INSTRUCTOR:
            if "entered_by" not in fields:
                fields.append("entered_by")
        return fields

    def save_model(self, request, obj, form, change):
        if not obj.entered_by_id or request.user.role == ROLE_INSTRUCTOR:
            obj.entered_by = request.user
        super().save_model(request, obj, form, change)
