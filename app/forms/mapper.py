from __future__ import annotations

from app.config.settings import UserProfile
from app.core.models import FieldInputType, FormField
from app.forms.models import FormInspectionResult, FormMappingResult, RawFormField


SENSITIVE_TERMS = {
    "salary",
    "pretensao",
    "pretensao salarial",
    "authorization",
    "autorizacao",
    "work authorization",
    "cover",
    "carta",
    "termo",
    "terms",
    "aceito",
}


def map_form_fields(
    inspection: FormInspectionResult,
    profile: UserProfile,
    resume_pdf_path: str | None = None,
) -> FormMappingResult:
    mapped_fields = [
        _map_field(field, profile=profile, resume_pdf_path=resume_pdf_path)
        for field in inspection.fields
    ]
    confidence_values = [field.confidence for field in mapped_fields]
    confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    risks = list(inspection.risks)
    if any(field.requires_human_review for field in mapped_fields):
        risks.append("One or more fields require human review before any application action.")

    return FormMappingResult(
        url=inspection.url,
        fields=mapped_fields,
        submit_button_selector=inspection.submit_button_selector,
        visited_pages=inspection.visited_pages,
        page_type=inspection.page_type,
        risks=risks,
        confidence=round(confidence, 4),
    )


def _map_field(
    field: RawFormField,
    profile: UserProfile,
    resume_pdf_path: str | None,
) -> FormField:
    normalized = _field_text(field)
    input_type = _input_type(field.input_type)
    sensitive = _is_sensitive(field, normalized, input_type)

    mapped_key, proposed_value, confidence = _simple_profile_mapping(
        normalized=normalized,
        profile=profile,
        input_type=input_type,
        resume_pdf_path=resume_pdf_path,
    )
    requires_review = sensitive or not proposed_value or confidence < 0.8
    reason = _reason_for_field(
        sensitive=sensitive,
        proposed_value=proposed_value,
        confidence=confidence,
    )

    return FormField(
        field_id=field.field_id,
        label=field.label or field.html_name or field.field_id,
        html_name=field.html_name,
        target_selector=field.target_selector,
        input_type=input_type,
        mapped_profile_key=mapped_key,
        proposed_value=proposed_value,
        confidence=confidence,
        requires_human_review=requires_review,
        reason=reason,
    )


def _simple_profile_mapping(
    normalized: str,
    profile: UserProfile,
    input_type: FieldInputType,
    resume_pdf_path: str | None,
) -> tuple[str | None, str | None, float]:
    if input_type == FieldInputType.FILE:
        return "resume.pdf_path", resume_pdf_path, 0.5
    if _contains_any(normalized, {"nome completo", "full name", "name"}):
        value = f"{profile.personal.first_name} {profile.personal.last_name}".strip()
        return "personal.full_name", value, 0.95
    if _contains_any(normalized, {"first name", "primeiro nome"}):
        return "personal.first_name", profile.personal.first_name, 0.95
    if _contains_any(normalized, {"last name", "sobrenome"}):
        return "personal.last_name", profile.personal.last_name, 0.95
    if _contains_any(normalized, {"email", "e-mail"}):
        return "personal.email", profile.personal.email, 0.99
    if _contains_any(normalized, {"telefone", "phone", "celular"}):
        return "personal.phone", profile.personal.phone, 0.95
    if _contains_any(normalized, {"cidade", "city"}):
        return "personal.city", profile.personal.city, 0.9
    if "linkedin" in normalized:
        return "personal.linkedin", profile.personal.linkedin, 0.95
    if "github" in normalized:
        return "personal.github", profile.personal.github, 0.95
    if _contains_any(normalized, {"portfolio", "site"}):
        return "personal.portfolio", profile.personal.portfolio, 0.85
    if _contains_any(normalized, {"pretensao", "salary"}):
        return "answers.salary_expectation", profile.answers.salary_expectation, 0.4
    if _contains_any(normalized, {"autorizacao", "authorization"}):
        return "answers.work_authorization", profile.answers.work_authorization, 0.4
    if _contains_any(normalized, {"carta", "cover"}):
        return "answers.cover_letter_template", profile.answers.cover_letter_template, 0.4
    return None, None, 0.0


def _input_type(value: str) -> FieldInputType:
    normalized = value.lower()
    if normalized == "textarea":
        return FieldInputType.TEXTAREA
    if normalized == "select":
        return FieldInputType.SELECT
    try:
        return FieldInputType(normalized)
    except ValueError:
        return FieldInputType.UNKNOWN


def _is_sensitive(field: RawFormField, normalized: str, input_type: FieldInputType) -> bool:
    if input_type in {FieldInputType.FILE, FieldInputType.CHECKBOX, FieldInputType.TEXTAREA}:
        return True
    return any(term in normalized for term in SENSITIVE_TERMS)


def _field_text(field: RawFormField) -> str:
    return " ".join(
        part.lower()
        for part in [
            field.field_id,
            field.label,
            field.html_name or "",
            field.placeholder or "",
            field.input_type,
        ]
        if part
    )


def _contains_any(text: str, needles: set[str]) -> bool:
    return any(needle in text for needle in needles)


def _reason_for_field(sensitive: bool, proposed_value: str | None, confidence: float) -> str:
    if sensitive:
        return "Sensitive, subjective, upload, legal, or open-ended field; human review required."
    if not proposed_value:
        return "No safe profile value was found; human review required."
    if confidence < 0.8:
        return "Low mapping confidence; human review required."
    return "Mapped from profile with high confidence."
