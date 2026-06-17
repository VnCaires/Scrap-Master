from app.config.settings import load_profile
from app.core.models import ApplicationStatus
from app.forms import FormInspectionResult, RawFormField, map_form_fields
from app.review import apply_field_edits, build_review_draft, normalize_review_decision


def test_review_draft_never_marks_submitted() -> None:
    profile = load_profile("config/profile.example.yaml")
    mapping = map_form_fields(
        FormInspectionResult(
            url="file:///fake.html",
            fields=[
                RawFormField(
                    field_id="email",
                    label="E-mail",
                    html_name="email",
                    input_type="email",
                )
            ],
        ),
        profile,
    )

    draft = build_review_draft(mapping)

    assert draft.status == ApplicationStatus.NEEDS_REVIEW
    assert draft.submitted is False


def test_normalize_review_decision() -> None:
    assert normalize_review_decision("approve") == ApplicationStatus.APPROVED
    assert normalize_review_decision("skip") == ApplicationStatus.SKIPPED
    assert normalize_review_decision("draft") == ApplicationStatus.NEEDS_REVIEW


def test_apply_field_edits_records_reviewed_values() -> None:
    profile = load_profile("config/profile.example.yaml")
    mapping = map_form_fields(
        FormInspectionResult(
            url="file:///fake.html",
            fields=[
                RawFormField(
                    field_id="salary_expectation",
                    label="Pretensao salarial",
                    html_name="salary_expectation",
                    input_type="text",
                )
            ],
        ),
        profile,
    )
    draft = build_review_draft(mapping)

    updated = apply_field_edits(draft, {"salary_expectation": "R$ 10.000 CLT"})

    assert updated.fields[0].proposed_value == "R$ 10.000 CLT"
    assert updated.fields[0].requires_human_review is False
    assert updated.edited_fields[0].field_id == "salary_expectation"
