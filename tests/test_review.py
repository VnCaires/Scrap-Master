from app.config.settings import load_profile
from app.core.models import ApplicationStatus
from app.forms import FormInspectionResult, RawFormField, map_form_fields
from app.review import build_review_draft, normalize_review_decision


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
