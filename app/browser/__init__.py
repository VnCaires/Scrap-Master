"""Safe local browser inspection package."""

from app.browser.manager import (
    BrowserAutomationError,
    apply_reviewed_form_page,
    fill_form_page,
    inspect_form_page,
)

__all__ = [
    "BrowserAutomationError",
    "apply_reviewed_form_page",
    "fill_form_page",
    "inspect_form_page",
]
