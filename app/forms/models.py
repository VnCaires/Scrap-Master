from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.models import FormField


class RawFormField(BaseModel):
    field_id: str
    label: str = ""
    html_name: str | None = None
    input_type: str = "unknown"
    placeholder: str | None = None
    target_selector: str | None = None


class FormInspectionResult(BaseModel):
    url: str
    fields: list[RawFormField] = Field(default_factory=list)
    submit_button_selector: str | None = None
    visited_pages: list[str] = Field(default_factory=list)
    page_type: str = "apply_form"
    risks: list[str] = Field(default_factory=list)
    submitted: bool = False


class FormMappingResult(BaseModel):
    url: str
    fields: list[FormField] = Field(default_factory=list)
    submit_button_selector: str | None = None
    visited_pages: list[str] = Field(default_factory=list)
    page_type: str = "apply_form"
    risks: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class FormFillResult(BaseModel):
    url: str
    filled_fields: list[FormField] = Field(default_factory=list)
    pending_review_fields: list[FormField] = Field(default_factory=list)
    attached_files: list[str] = Field(default_factory=list)
    visited_pages: list[str] = Field(default_factory=list)
    flow_stage: str = "apply_form"
    screenshot_path: str | None = None
    submitted: bool = False
    risks: list[str] = Field(default_factory=list)
