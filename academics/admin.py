from django.contrib import admin

from .models import (
    Course,
    CourseContribution,
    CourseOffering,
    Department,
    LearningOutcome,
    LearningOutcomeMapping,
    ProgramOutcome,
)


class ProgramOutcomeInline(admin.TabularInline):
    model = ProgramOutcome
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "head")
    search_fields = ("code", "name")
    inlines = [ProgramOutcomeInline]


@admin.register(ProgramOutcome)
class ProgramOutcomeAdmin(admin.ModelAdmin):
    list_display = ("code", "short_name", "department")
    list_filter = ("department",)
    search_fields = ("short_name", "description")


class LearningOutcomeInline(admin.TabularInline):
    model = LearningOutcome
    extra = 0


class CourseContributionInline(admin.TabularInline):
    model = CourseContribution
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "credits", "ects")
    list_filter = ("department",)
    search_fields = ("code", "name")
    inlines = [LearningOutcomeInline, CourseContributionInline]


class LearningOutcomeMappingInline(admin.TabularInline):
    model = LearningOutcomeMapping
    extra = 0


@admin.register(LearningOutcome)
class LearningOutcomeAdmin(admin.ModelAdmin):
    list_display = ("__str__", "course", "description")
    list_filter = ("course",)
    inlines = [LearningOutcomeMappingInline]


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ("course", "year", "semester", "section")
    list_filter = ("year", "semester", "course__department")
    search_fields = ("course__code", "course__name")
    filter_horizontal = ("instructors",)
