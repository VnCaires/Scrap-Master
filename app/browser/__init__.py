"""Safe local browser inspection package."""

from app.browser.manager import BrowserAutomationError, inspect_form_page

__all__ = ["BrowserAutomationError", "inspect_form_page"]
