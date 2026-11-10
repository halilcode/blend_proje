from django.shortcuts import render

from academics.models import ProgramOutcome

from .models import Grade
from .scoring import learning_outcome_scores, round_score, student_po_profile


def student_course_details(student):
    """
    Per-course breakdown for one student: every assessment of each course they
    are enrolled in (with their grade, or None if not graded yet) and the
    course's learning outcome scores, computed by the same scoring service
    that feeds the PO profile.
    """
    details = []
    enrollments = (
        student.enrollments
        .select_related("offering__course")
        .order_by("offering__course__code", "-offering__year")
    )
    for enrollment in enrollments:
        offering = enrollment.offering
        grades = {
            grade.assessment_id: grade
            for grade in Grade.objects.filter(enrollment=enrollment).select_related("assessment")
        }
        assessments = []
        for assessment in offering.assessments.all():
            grade = grades.get(assessment.id)
            assessments.append({
                "assessment": assessment,
                "score": grade.score if grade else None,
                "percentage": round_score(grade.percentage) if grade else None,
            })

        lo_scores = learning_outcome_scores(enrollment)
        learning_outcomes = [
            {"outcome": lo, "score": round_score(lo_scores.get(lo.id))}
            for lo in offering.course.learning_outcomes.all()
        ]

        details.append({
            "offering": offering,
            "course": offering.course,
            "assessments": assessments,
            "graded_count": len(grades),
            "learning_outcomes": learning_outcomes,
        })
    return details


def home(request):
    """Landing page. Students see their program outcome profile and their grades."""
    context = {}
    user = request.user
    if user.is_authenticated and user.is_student:
        profile = student_po_profile(user)
        outcomes = ProgramOutcome.objects.filter(department=user.department) if user.department_id else (
            ProgramOutcome.objects.filter(id__in=profile.keys())
        )
        po_rows = []
        for po in outcomes:
            score = round_score(profile.get(po.id))
            po_rows.append({
                "outcome": po,
                "score": score,
                "score_percent": f"{score:.1f}" if score is not None else None,
                "has_score": score is not None,
            })
        context["po_rows"] = po_rows
        context["course_details"] = student_course_details(user)
    return render(request, "home.html", context)
