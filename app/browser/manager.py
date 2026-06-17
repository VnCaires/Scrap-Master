from __future__ import annotations

from pathlib import Path

from app.core.models import FieldInputType, FormField
from app.forms.models import FormFillResult, FormInspectionResult, RawFormField


class BrowserAutomationError(RuntimeError):
    """Raised when local browser inspection cannot run safely."""


async def inspect_form_page(
    url: str | Path,
    headless: bool = True,
    screenshot_path: str | Path | None = None,
) -> FormInspectionResult:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise BrowserAutomationError(
            "Playwright is not installed. Install browser dependencies with: "
            "python -m pip install -e \".[browser]\""
        ) from exc

    target_url = _to_browser_url(url)
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless)
            page = await browser.new_page()
            await page.goto(target_url, wait_until="domcontentloaded")
            fields = await page.evaluate(_FORM_FIELD_SCRIPT)
            submit_selector = await page.evaluate(_SUBMIT_SELECTOR_SCRIPT)
            if screenshot_path:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            await browser.close()
    except Exception as exc:
        raise BrowserAutomationError(
            "Playwright could not inspect the page. If browsers are missing, run: "
            "python -m playwright install chromium"
        ) from exc

    return FormInspectionResult(
        url=target_url,
        fields=[RawFormField.model_validate(field) for field in fields],
        submit_button_selector=submit_selector,
        risks=["Inspection mode only; no submit action was performed."],
        submitted=False,
    )


async def fill_form_page(
    url: str | Path,
    fields: list[FormField],
    headless: bool = True,
    screenshot_path: str | Path | None = None,
) -> FormFillResult:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        raise BrowserAutomationError(
            "Playwright is not installed. Install browser dependencies with: "
            "python -m pip install -e \".[browser]\""
        ) from exc

    target_url = _to_browser_url(url)
    autofill_fields = [
        field
        for field in fields
        if not field.requires_human_review
        and field.proposed_value
        and field.target_selector
        and field.input_type in {FieldInputType.TEXT, FieldInputType.EMAIL, FieldInputType.TEL}
    ]
    pending_review_fields = [field for field in fields if field not in autofill_fields]

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless)
            page = await browser.new_page()
            await page.goto(target_url, wait_until="domcontentloaded")
            for field in autofill_fields:
                await page.locator(field.target_selector).fill(field.proposed_value or "")
            if screenshot_path:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            await browser.close()
    except Exception as exc:
        raise BrowserAutomationError(
            "Playwright could not fill the page. If browsers are missing, run: "
            "python -m playwright install chromium"
        ) from exc

    return FormFillResult(
        url=target_url,
        filled_fields=autofill_fields,
        pending_review_fields=pending_review_fields,
        screenshot_path=str(screenshot_path) if screenshot_path else None,
        submitted=False,
        risks=["Autofill mode only; submit was not triggered."],
    )


def _to_browser_url(url: str | Path) -> str:
    text = str(url)
    if text.startswith(("http://", "https://", "file://")):
        return text

    path = Path(text)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve().as_uri()


_FORM_FIELD_SCRIPT = """
() => {
  const controls = Array.from(document.querySelectorAll('input, textarea, select'));
  const labelFor = (el) => {
    if (el.labels && el.labels.length) {
      return Array.from(el.labels).map((label) => label.innerText.trim()).join(' ').trim();
    }
    if (el.id) {
      const label = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
      if (label) return label.innerText.trim();
    }
    return '';
  };
  const inputType = (el) => {
    const tag = el.tagName.toLowerCase();
    if (tag === 'textarea') return 'textarea';
    if (tag === 'select') return 'select';
    return (el.getAttribute('type') || 'text').toLowerCase();
  };
  return controls.map((el, index) => ({
    field_id: el.id || el.name || `field_${index + 1}`,
    label: labelFor(el),
    html_name: el.getAttribute('name'),
    input_type: inputType(el),
    placeholder: el.getAttribute('placeholder'),
    target_selector: el.id
      ? `#${CSS.escape(el.id)}`
      : (el.getAttribute('name')
          ? `${el.tagName.toLowerCase()}[name="${CSS.escape(el.getAttribute('name'))}"]`
          : null)
  }));
}
"""

_SUBMIT_SELECTOR_SCRIPT = """
() => {
  const submit = document.querySelector('button[type="submit"], input[type="submit"]');
  if (!submit) return null;
  if (submit.id) return `#${CSS.escape(submit.id)}`;
  if (submit.name) return `[name="${CSS.escape(submit.name)}"]`;
  return 'button[type="submit"], input[type="submit"]';
}
"""
