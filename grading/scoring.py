"""
Score calculation: grades → learning outcomes → program outcomes.

Every step uses the same rule:

    score = Σ(weight × score) ÷ Σ weights

Only sources that actually have a value take part, so an LO whose assessments
are not graded yet gets no score (rather than a score of 0), and an LO with only
some graded assessments is averaged over those.

Worked example from the project brief (CSE 311, Midterm = 90, Project = 80):

    LO1 = (90×60 + 80×40) ÷ 100          = 86.0
    LO2 = (90×40 + 80×100) ÷ 140         = 82.86
    PO1 = (86.0×100 + 82.86×50) ÷ 150    = 84.95
    PO2 = (82.86×100) ÷ 100              = 82.86
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from academics.models import CourseContribution, LearningOutcomeMapping

from .models import AssessmentMapping, Grade

# Contribution level used for a course that feeds a PO (through its LOs) but has
# no explicit CourseContribution row for it.
DEFAULT_CONTRIBUTION_LEVEL = 1


def weighted_average(pairs):
    """Weighted average of (weight, value) pairs; None if there is nothing to average."""
    total_weight = Decimal(0)
    total = Decimal(0)
    for weight, value in pairs:
        weight = Decimal(weight)
        total_weight += weight
        total += weight * Decimal(value)
    if total_weight == 0:
        return None
    return total / total_weight


def round_score(value, places=1):
    """Round a score for display (half-up, like a grade sheet)."""
    if value is None:
        return None
    return Decimal(value).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def assessment_scores(enrollment):
    """{assessment_id: score as a percentage (0–100)} for the enrollment's graded assessments."""
    grades = Grade.objects.filter(enrollment=enrollment).select_related("assessment")
    return {grade.assessment_id: grade.percentage for grade in grades}


def learning_outcome_scores(enrollment, graded=None):
    """{learning_outcome_id: score} for one student in one course offering."""
    if graded is None:
        graded = assessment_scores(enrollment)
    if not graded:
        return {}

    pairs_by_lo = defaultdict(list)
    mappings = AssessmentMapping.objects.filter(assessment_id__in=graded.keys()).values_list(
        "learning_outcome_id", "assessment_id", "weight"
    )
    for lo_id, assessment_id, weight in mappings:
        pairs_by_lo[lo_id].append((weight, graded[assessment_id]))

    return {lo_id: weighted_average(pairs) for lo_id, pairs in pairs_by_lo.items()}


def program_outcome_scores(enrollment, lo_scores=None):
    """{program_outcome_id: score} for one student, based on a single course offering."""
    if lo_scores is None:
        lo_scores = learning_outcome_scores(enrollment)
    if not lo_scores:
        return {}

    pairs_by_po = defaultdict(list)
    mappings = LearningOutcomeMapping.objects.filter(
        learning_outcome_id__in=lo_scores.keys()
    ).values_list("program_outcome_id", "learning_outcome_id", "weight")
    for po_id, lo_id, weight in mappings:
        pairs_by_po[po_id].append((weight, lo_scores[lo_id]))

    return {po_id: weighted_average(pairs) for po_id, pairs in pairs_by_po.items()}


def student_po_profile(student):
    """
    {program_outcome_id: score} across every course the student has taken.

    Per-course PO scores are combined with each course's 1–5 contribution level
    for that PO (CourseContribution).
    """
    enrollments = list(student.enrollments.select_related("offering"))
    if not enrollments:
        return {}

    course_ids = {e.offering.course_id for e in enrollments}
    levels = {
        (course_id, po_id): level
        for course_id, po_id, level in CourseContribution.objects.filter(
            course_id__in=course_ids
        ).values_list("course_id", "program_outcome_id", "level")
    }

    pairs_by_po = defaultdict(list)
    for enrollment in enrollments:
        course_id = enrollment.offering.course_id
        for po_id, score in program_outcome_scores(enrollment).items():
            level = levels.get((course_id, po_id), DEFAULT_CONTRIBUTION_LEVEL)
            pairs_by_po[po_id].append((level, score))

    return {po_id: weighted_average(pairs) for po_id, pairs in pairs_by_po.items()}
