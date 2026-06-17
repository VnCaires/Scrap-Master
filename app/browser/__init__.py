"""Safe local browser inspection package."""

from app.browser.manager import BrowserAutomationError, fill_form_page, inspect_form_page

__all__ = ["BrowserAutomationError", "fill_form_page", "inspect_form_page"]
