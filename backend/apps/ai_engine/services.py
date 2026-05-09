"""AI service: builds context from a case and calls the provider."""
from __future__ import annotations

from apps.cases.models import Case

from .models import AIInsight
from .providers import generate


def _case_context(case: Case) -> dict:
    iocs = list(case.iocs.values("kind", "value", "severity")[:200])
    jobs = []
    risk_max = 0
    for ev in case.evidence.all():
        for j in ev.analysis_jobs.all():
            risk_max = max(risk_max, j.risk_score)
            jobs.append({"evidence": ev.name, "status": j.status,
                         "risk": j.risk_score, "os": j.detected_os})
    return {"case_code": case.code, "title": case.title,
            "severity": case.severity, "iocs": iocs,
            "jobs": jobs, "max_risk_score": risk_max}


def summarize_case(case: Case, *, actor=None) -> AIInsight:
    ctx = _case_context(case)
    prompt = ("Summarise the suspicious behaviour observed in this DFIR case. "
              "Provide a concise, actionable findings list.\n"
              f"Context: {ctx}")
    text, model = generate(prompt, context=ctx)
    return AIInsight.objects.create(
        case=case, kind=AIInsight.Kind.SUMMARY, title="Behaviour Summary",
        content=text, model_used=model, prompt_excerpt=prompt[:1000],
        metadata={"context": ctx}, created_by=actor,
    )


def classify_threat(case: Case, *, actor=None) -> AIInsight:
    ctx = _case_context(case)
    prompt = ("Classify the most likely threat type for this case "
              "(e.g. ransomware, info-stealer, RAT, supply-chain, insider). "
              "Justify briefly.\n"
              f"Context: {ctx}")
    text, model = generate(prompt, context=ctx)
    return AIInsight.objects.create(
        case=case, kind=AIInsight.Kind.CLASSIFICATION, title="Threat Classification",
        content=text, model_used=model, prompt_excerpt=prompt[:1000],
        metadata={"context": ctx}, created_by=actor,
    )


def recommend_next_steps(case: Case, *, actor=None) -> AIInsight:
    ctx = _case_context(case)
    prompt = ("Suggest the next 5 investigation steps an analyst should take. "
              f"Context: {ctx}")
    text, model = generate(prompt, context=ctx)
    return AIInsight.objects.create(
        case=case, kind=AIInsight.Kind.RECOMMENDATION,
        title="Investigation Recommendations",
        content=text, model_used=model, prompt_excerpt=prompt[:1000],
        metadata={"context": ctx}, created_by=actor,
    )
