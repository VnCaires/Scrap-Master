"""Application form mapping package."""

from app.forms.mapper import map_form_fields
from app.forms.models import FormInspectionResult, FormMappingResult, RawFormField

__all__ = [
    "FormInspectionResult",
    "FormMappingResult",
    "RawFormField",
    "map_form_fields",
]
