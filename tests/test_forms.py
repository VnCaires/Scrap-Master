from app.config.settings import load_profile
from app.core.models import FieldInputType
from app.forms import FormInspectionResult, RawFormField, map_form_fields


def test_form_mapper_maps_simple_profile_fields() -> None:
    profile = load_profile("config/profile.example.yaml")
    inspection = FormInspectionResult(
        url="file:///fake.html",
        fields=[
            RawFormField(
                field_id="email",
                label="E-mail",
                html_name="email",
                input_type="email",
            ),
            RawFormField(
                field_id="city",
                label="Cidade",
                html_name="city",
                input_type="text",
            ),
        ],
    )

    mapping = map_form_fields(inspection, profile)

    assert mapping.fields[0].mapped_profile_key == "personal.email"
    assert mapping.fields[0].requires_human_review is False
    assert mapping.fields[1].mapped_profile_key == "personal.city"


def test_form_mapper_marks_sensitive_fields_for_review() -> None:
    profile = load_profile("config/profile.example.yaml")
    inspection = FormInspectionResult(
        url="file:///fake.html",
        fields=[
            RawFormField(
                field_id="salary_expectation",
                label="Pretensao salarial",
                html_name="salary_expectation",
                input_type="text",
            ),
            RawFormField(
                field_id="terms",
                label="Aceito os termos",
                html_name="terms",
                input_type="checkbox",
            ),
        ],
    )

    mapping = map_form_fields(inspection, profile)

    assert mapping.fields[0].requires_human_review is True
    assert mapping.fields[0].mapped_profile_key == "answers.salary_expectation"
    assert mapping.fields[1].input_type == FieldInputType.CHECKBOX
    assert mapping.fields[1].requires_human_review is True
