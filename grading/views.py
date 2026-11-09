from django.shortcuts import render

from academics.models import ProgramOutcome

from .scoring import round_score, student_po_profile


def home(request):
    """Landing page. Students see their program outcome profile."""
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
    return render(request, "home.html", context)
