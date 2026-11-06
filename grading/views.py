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
        context["po_rows"] = [
            {"outcome": po, "score": round_score(profile.get(po.id))} for po in outcomes
        ]
    return render(request, "home.html", context)
