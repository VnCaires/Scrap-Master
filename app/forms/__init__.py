"""Application form mapping package."""

from app.forms.mapper import map_form_fields
from app.forms.models import FormFillResult, FormInspectionResult, FormMappingResult, RawFormField

__all__ = [
    "FormFillResult",
    "FormInspectionResult",
    "FormMappingResult",
    "RawFormField",
    "map_form_fields",
]
