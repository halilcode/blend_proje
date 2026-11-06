from django.contrib import admin

from .models import Assessment, AssessmentMapping, Enrollment, Grade


class AssessmentMappingInline(admin.TabularInline):
    model = AssessmentMapping
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "offering", "max_score", "date")
    list_filter = ("kind", "offering__year", "offering__semester", "offering__course")
    search_fields = ("name", "offering__course__code")
    inlines = [AssessmentMappingInline]


class GradeInline(admin.TabularInline):
    model = Grade
    extra = 0
    fields = ("assessment", "score", "entered_by", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "offering", "enrolled_at")
    list_filter = ("offering__year", "offering__semester", "offering__course")
    search_fields = ("student__username", "student__last_name", "student__student_number")
    inlines = [GradeInline]


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("enrollment", "assessment", "score", "entered_by", "updated_at")
    list_filter = ("assessment__offering__course", "assessment__kind")
    search_fields = ("enrollment__student__username", "enrollment__student__last_name")
