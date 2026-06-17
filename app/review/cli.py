from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.models import ApplicationStatus, FormField
from app.forms.models import FormMappingResult


class ReviewDraft(BaseModel):
    url: str
    status: ApplicationStatus = ApplicationStatus.NEEDS_REVIEW
    fields: list[FormField] = Field(default_factory=list)
    edited_fields: list[FormField] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    resume_attached: bool = False
    resume_path: str | None = None
    screenshot_path: str | None = None
    submitted: bool = False


def build_review_draft(mapping: FormMappingResult) -> ReviewDraft:
    return ReviewDraft(
        url=mapping.url,
        fields=mapping.fields,
        risks=mapping.risks,
        submitted=False,
    )


def render_review_draft(draft: ReviewDraft) -> str:
    lines = [
        f"Review draft for: {draft.url}",
        f"Status: {draft.status.value}",
        "Submitted: no",
        "",
        "Fields:",
    ]
    for field in draft.fields:
        proposed = field.proposed_value if field.proposed_value else "<empty>"
        review = "yes" if field.requires_human_review else "no"
        lines.append(
            f"- {field.label} [{field.input_type.value}] -> {field.mapped_profile_key or '<unmapped>'} "
            f"= {proposed} | review: {review}"
        )

    if draft.risks:
        lines.extend(["", "Risks:"])
        lines.extend(f"- {risk}" for risk in draft.risks)

    return "\n".join(lines)


def apply_field_edits(draft: ReviewDraft, edits: dict[str, str]) -> ReviewDraft:
    edited_fields: list[FormField] = []
    updated_fields: list[FormField] = []
    for field in draft.fields:
        if field.field_id in edits:
            updated = field.model_copy(
                update={
                    "proposed_value": edits[field.field_id],
                    "requires_human_review": False,
                    "confidence": 1.0,
                    "reason": "Edited and approved during human CLI review.",
                }
            )
            updated_fields.append(updated)
            edited_fields.append(updated)
        else:
            updated_fields.append(field)

    return draft.model_copy(update={"fields": updated_fields, "edited_fields": edited_fields})


def normalize_review_decision(value: str) -> ApplicationStatus:
    normalized = value.strip().lower()
    if normalized == "approve":
        return ApplicationStatus.APPROVED
    if normalized == "skip":
        return ApplicationStatus.SKIPPED
    if normalized == "draft":
        return ApplicationStatus.NEEDS_REVIEW
    raise ValueError("decision must be approve, skip, or draft")
