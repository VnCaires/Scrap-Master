from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import typer
from loguru import logger

from app.browser import (
    BrowserAutomationError,
    apply_reviewed_form_page,
    fill_form_page,
    inspect_form_flow,
    inspect_form_page,
)
from app.config.settings import load_profile, load_settings
from app.core.models import ApplicationStatus, ContractType, FieldInputType, JobPosting, RemoteType, Seniority
from app.documents import ResumeError, parse_resume_pdf
from app.forms import FormFillResult, map_form_fields
from app.llm import CompatibilityEvaluation, create_llm_client
from app.observability import configure_logging
from app.ranking import rank_jobs
from app.review import apply_field_edits, build_review_draft, normalize_review_decision, render_review_draft
from app.security import mask_email, mask_name
from app.sources import get_enabled_source_adapters
from app.storage import (
    get_application_attempt_record,
    init_database,
    list_application_attempt_records,
    job_from_record,
    list_job_posting_records,
    save_application_attempt,
    save_job_match,
    save_job_postings,
    save_run_history,
    session_scope,
)

app = typer.Typer(
    help="Scrap Master foundation CLI. No real scraping or auto-submit is implemented yet."
)


@app.callback()
def main(verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logs.")) -> None:
    configure_logging(verbose=verbose)


@app.command()
def init(force: bool = typer.Option(False, "--force", help="Overwrite existing local config files.")) -> None:
    """Create local config files from examples."""
    _copy_example(Path("config/settings.example.yaml"), Path("config/settings.yaml"), force)
    _copy_example(Path("config/profile.example.yaml"), Path("config/profile.yaml"), force)
    for directory in ["data/input", "data/output", "data/logs", "data/cache"]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    typer.echo("Project configuration initialized.")


@app.command("init-db")
def init_db(
    settings: Path = typer.Option(
        Path("config/settings.yaml"),
        "--settings",
        "-s",
        help="Path to settings YAML.",
    )
) -> None:
    """Create the SQLite database schema."""
    loaded = load_settings(settings)
    init_database(loaded.storage.database_url)
    logger.info("Database initialized at {}", loaded.storage.database_url)
    typer.echo(f"Database initialized: {loaded.storage.database_url}")


@app.command("config-check")
def config_check(
    settings: Path = typer.Option(
        Path("config/settings.yaml"),
        "--settings",
        "-s",
        help="Path to settings YAML.",
    )
) -> None:
    """Validate settings and show enabled sources."""
    loaded = load_settings(settings)
    enabled = ", ".join(source.name for source in loaded.enabled_sources()) or "none"
    logger.info("Settings loaded from {}", settings)
    typer.echo(f"Settings OK. Enabled sources: {enabled}")


@app.command("validate-profile")
def validate_profile(
    profile: Path = typer.Option(
        Path("config/profile.yaml"),
        "--profile",
        "-p",
        help="Path to profile YAML.",
    )
) -> None:
    """Validate a user profile YAML file."""
    loaded = load_profile(profile)
    logger.info(
        "Profile loaded for {} ({})",
        mask_name(loaded.personal.first_name, loaded.personal.last_name),
        mask_email(loaded.personal.email),
    )
    review_fields = loaded.fields_requiring_review()
    typer.echo(f"Profile OK: {loaded.personal.first_name} {loaded.personal.last_name}")
    if review_fields:
        typer.echo(f"Fields requiring review: {', '.join(review_fields)}")


@app.command("parse-resume")
def parse_resume(
    pdf: Path = typer.Option(..., "--pdf", help="Path to resume PDF."),
    max_size_mb: int = typer.Option(5, "--max-size-mb", min=1),
    output: Path | None = typer.Option(
        Path("data/output/resume_parsed.txt"),
        "--output",
        "-o",
        help="Path to write extracted resume text.",
    ),
) -> None:
    """Validate, extract, and optionally save text from a resume PDF."""
    try:
        parsed = parse_resume_pdf(pdf, max_size_mb=max_size_mb, output_text_path=output)
    except ResumeError as exc:
        logger.warning("Resume parsing failed: {}", exc)
        typer.echo(f"Resume error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    logger.info("Resume parsed: {} pages, {} bytes", parsed.page_count, parsed.size_bytes)
    typer.echo(
        f"Resume OK: {parsed.page_count} page(s), {parsed.size_bytes} bytes, "
        f"{len(parsed.text)} extracted characters"
    )
    if parsed.extracted_text_path:
        typer.echo(f"Extracted text saved: {parsed.extracted_text_path}")


@app.command()
def search(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Job search keyword."),
    limit: int = typer.Option(10, "--limit", "-l", min=1, help="Maximum number of jobs."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
) -> None:
    """Search configured sources and persist deduplicated jobs."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)
    jobs = asyncio.run(_search_jobs(loaded_settings, keyword, limit))
    with session_scope(loaded_settings.storage.database_url) as session:
        records = save_job_postings(session, jobs)
    logger.info("Search returned {} jobs for keyword '{}'", len(records), keyword)
    typer.echo(f"Saved {len(records)} job(s).")
    for index, job in enumerate(jobs, start=1):
        company = f" at {job.company}" if job.company else ""
        typer.echo(f"{index}. {job.title}{company} - {job.url}")


@app.command()
def rank(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Job ranking keyword."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
    profile: Path | None = typer.Option(None, "--profile", "-p", help="Path to profile YAML."),
) -> None:
    """Rank persisted jobs with explainable local scoring and optional mock LLM signals."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)
    loaded_profile = load_profile(profile or loaded_settings.profile_path)
    matches_created = _rank_persisted_jobs(loaded_settings, loaded_profile, keyword)
    typer.echo(f"Created {matches_created} job match(es).")


@app.command()
def run(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Job search keyword."),
    limit: int = typer.Option(10, "--limit", "-l", min=1, help="Maximum number of jobs."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
) -> None:
    """Run search, persistence, ranking, and stop before browser automation."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)
    loaded_profile = load_profile(loaded_settings.profile_path)
    effective_limit = min(limit, loaded_settings.runtime.max_jobs_per_source)
    jobs = asyncio.run(_search_jobs(loaded_settings, keyword, effective_limit))
    with session_scope(loaded_settings.storage.database_url) as session:
        records = save_job_postings(session, jobs)

    matches_created = _rank_persisted_jobs(loaded_settings, loaded_profile, keyword)
    with session_scope(loaded_settings.storage.database_url) as session:
        save_run_history(
            session=session,
            keyword=keyword,
            source_count=len(loaded_settings.enabled_sources()),
            jobs_found=len(records),
            matches_created=matches_created,
        )

    logger.info(
        "Run completed with human review required: {}",
        loaded_settings.runtime.require_human_review,
    )
    typer.echo(
        f"Found {len(records)} job(s), created {matches_created} match(es). "
        "Browser automation is not implemented yet."
    )


@app.command("inspect-form")
def inspect_form(
    url: str = typer.Option(..., "--url", help="Local HTML file or URL to inspect."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
    screenshot: Path | None = typer.Option(None, "--screenshot", help="Optional screenshot output path."),
) -> None:
    """Inspect a form without filling or submitting it."""
    loaded_settings = load_settings(settings)
    try:
        inspection = asyncio.run(
            inspect_form_page(
                url=url,
                headless=loaded_settings.runtime.headless,
                screenshot_path=screenshot,
            )
        )
    except BrowserAutomationError as exc:
        typer.echo(f"Browser error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Inspected: {inspection.url}")
    typer.echo(f"Submitted: {'yes' if inspection.submitted else 'no'}")
    typer.echo(f"Submit selector: {inspection.submit_button_selector or '<not found>'}")
    for field in inspection.fields:
        typer.echo(
            f"- {field.label or field.field_id} [{field.input_type}] "
            f"name={field.html_name or '<none>'}"
        )


@app.command("inspect-flow")
def inspect_flow(
    url: str = typer.Option(..., "--url", help="Local careers home or job page to inspect as a flow."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
    screenshot: Path | None = typer.Option(None, "--screenshot", help="Optional screenshot output path."),
) -> None:
    """Inspect a local multi-step careers flow without submitting anything."""
    loaded_settings = load_settings(settings)
    try:
        inspection = asyncio.run(
            inspect_form_flow(
                url=url,
                headless=loaded_settings.runtime.headless,
                screenshot_path=screenshot,
            )
        )
    except BrowserAutomationError as exc:
        typer.echo(f"Browser error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Flow ended at: {inspection.url}")
    typer.echo(f"Page type: {inspection.page_type}")
    typer.echo(f"Visited pages: {len(inspection.visited_pages)}")
    for visited in inspection.visited_pages:
        typer.echo(f"- visited {visited}")
    typer.echo(f"Submitted: {'yes' if inspection.submitted else 'no'}")
    typer.echo(f"Submit selector: {inspection.submit_button_selector or '<not found>'}")
    for field in inspection.fields:
        typer.echo(
            f"- {field.label or field.field_id} [{field.input_type}] "
            f"name={field.html_name or '<none>'}"
        )


@app.command()
def review(
    url: str = typer.Option(..., "--url", help="Local HTML file or URL to review."),
    profile: Path | None = typer.Option(None, "--profile", "-p", help="Path to profile YAML."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
    screenshot: Path | None = typer.Option(
        None,
        "--screenshot",
        help="Optional screenshot path for the reviewed local form.",
    ),
    decision: str | None = typer.Option(
        None,
        "--decision",
        help="Non-interactive decision: approve, skip, or draft.",
    ),
) -> None:
    """Create a local review draft and persist it without submitting anything."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)
    loaded_profile = load_profile(profile or loaded_settings.profile_path)

    try:
        inspection = asyncio.run(
            inspect_form_page(url=url, headless=loaded_settings.runtime.headless)
        )
    except BrowserAutomationError as exc:
        typer.echo(f"Browser error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    mapping = map_form_fields(
        inspection,
        profile=loaded_profile,
        resume_pdf_path=str(loaded_settings.resume_pdf_path),
    )
    draft = build_review_draft(mapping)
    typer.echo(render_review_draft(draft))

    edits = _collect_review_edits(draft, interactive=decision is None)
    if edits:
        draft = apply_field_edits(draft, edits)
        typer.echo(f"Edited fields: {', '.join(edits.keys())}")

    chosen = decision or typer.prompt("Decision [approve/skip/draft]", default="draft")
    try:
        status = normalize_review_decision(chosen)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    parsed_resume_path: str | None = None
    if status == ApplicationStatus.SKIPPED:
        apply_result = FormFillResult(
            url=inspection.url,
            pending_review_fields=draft.fields,
            submitted=False,
            risks=["Review was skipped; no local form changes were applied."],
        )
    else:
        if any(field.input_type == FieldInputType.FILE for field in draft.fields):
            try:
                parsed_resume = parse_resume_pdf(loaded_settings.resume_pdf_path)
                parsed_resume_path = str(parsed_resume.pdf_path)
                draft = draft.model_copy(
                    update={"resume_attached": True, "resume_path": parsed_resume_path}
                )
            except ResumeError as exc:
                logger.warning("Resume validation failed during review: {}", exc)
                typer.echo(f"Resume error: {exc}", err=True)
                raise typer.Exit(code=1) from exc

        try:
            apply_result = asyncio.run(
                apply_reviewed_form_page(
                    url=url,
                    fields=draft.fields,
                    edited_field_ids=set(edits),
                    resume_pdf_path=parsed_resume_path,
                    headless=loaded_settings.runtime.headless,
                    screenshot_path=screenshot,
                )
            )
        except BrowserAutomationError as exc:
            typer.echo(f"Browser error: {exc}", err=True)
            raise typer.Exit(code=1) from exc

    draft = draft.model_copy(update={"screenshot_path": apply_result.screenshot_path})

    with session_scope(loaded_settings.storage.database_url) as session:
        job_record = save_job_postings(session, [_local_form_job(inspection.url)])[0]
        attempt = save_application_attempt(
            session=session,
            job_record=job_record,
            status=status,
            review_required=True,
            result={
                "url": inspection.url,
                "status": status.value,
                "submitted": False,
                "fields": [field.model_dump(mode="json") for field in draft.fields],
                "edited_fields": [
                    field.model_dump(mode="json") for field in draft.edited_fields
                ],
                "filled_fields": [
                    field.model_dump(mode="json") for field in apply_result.filled_fields
                ],
                "pending_review_fields": [
                    field.model_dump(mode="json")
                    for field in apply_result.pending_review_fields
                ],
                "resume_attached": draft.resume_attached,
                "resume_path": draft.resume_path,
                "attached_files": apply_result.attached_files,
                "visited_pages": draft.visited_pages or apply_result.visited_pages,
                "page_type": draft.page_type,
                "flow_stage": apply_result.flow_stage,
                "screenshot_path": draft.screenshot_path,
                "risks": [*mapping.risks, *apply_result.risks],
            },
        )

    typer.echo(
        f"Saved application attempt {attempt.id} with status {status.value}. "
        "No submit action was performed."
    )


@app.command("fill-form")
def fill_form(
    url: str = typer.Option(..., "--url", help="Local HTML file or URL to fill."),
    profile: Path | None = typer.Option(None, "--profile", "-p", help="Path to profile YAML."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
    screenshot: Path | None = typer.Option(
        None,
        "--screenshot",
        help="Optional screenshot path for the filled local form.",
    ),
) -> None:
    """Fill only safe fields in a local form and save a review attempt without submitting."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)
    loaded_profile = load_profile(profile or loaded_settings.profile_path)

    try:
        inspection = asyncio.run(
            inspect_form_page(url=url, headless=loaded_settings.runtime.headless)
        )
        mapping = map_form_fields(
            inspection,
            profile=loaded_profile,
            resume_pdf_path=str(loaded_settings.resume_pdf_path),
        )
        fill_result = asyncio.run(
            fill_form_page(
                url=url,
                fields=mapping.fields,
                headless=loaded_settings.runtime.headless,
                screenshot_path=screenshot,
            )
        )
    except BrowserAutomationError as exc:
        typer.echo(f"Browser error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Filled form: {fill_result.url}")
    typer.echo(f"Submitted: {'yes' if fill_result.submitted else 'no'}")
    typer.echo(f"Filled fields: {len(fill_result.filled_fields)}")
    for field in fill_result.filled_fields:
        typer.echo(f"- filled {field.label} -> {field.proposed_value}")
    typer.echo(f"Pending review fields: {len(fill_result.pending_review_fields)}")
    for field in fill_result.pending_review_fields:
        typer.echo(f"- review {field.label}")
    if fill_result.screenshot_path:
        typer.echo(f"Screenshot: {fill_result.screenshot_path}")

    with session_scope(loaded_settings.storage.database_url) as session:
        job_record = save_job_postings(session, [_local_form_job(fill_result.url)])[0]
        attempt = save_application_attempt(
            session=session,
            job_record=job_record,
            status=ApplicationStatus.NEEDS_REVIEW,
            review_required=True,
            result={
                "url": fill_result.url,
                "status": ApplicationStatus.NEEDS_REVIEW.value,
                "submitted": False,
                "filled_fields": [field.model_dump(mode="json") for field in fill_result.filled_fields],
                "pending_review_fields": [
                    field.model_dump(mode="json") for field in fill_result.pending_review_fields
                ],
                "screenshot_path": fill_result.screenshot_path,
                "visited_pages": fill_result.visited_pages,
                "flow_stage": fill_result.flow_stage,
                "risks": fill_result.risks,
            },
        )

    typer.echo(
        f"Saved application attempt {attempt.id} with status needs_review. "
        "No submit action was performed."
    )


@app.command("attempts")
def attempts(
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
    limit: int = typer.Option(10, "--limit", "-l", min=1),
) -> None:
    """List persisted application attempts for local audit."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)

    with session_scope(loaded_settings.storage.database_url) as session:
        records = list_application_attempt_records(session)[:limit]

    if not records:
        typer.echo("No application attempts found.")
        return

    typer.echo("Application attempts:")
    for record in records:
        submitted = record.submitted_at.isoformat() if record.submitted_at else "no"
        typer.echo(
            f"- #{record.id} job={record.job_id} status={record.status} "
            f"review_required={record.review_required} submitted={submitted} "
            f"created_at={record.created_at.isoformat()}"
        )


@app.command("attempt-show")
def attempt_show(
    attempt_id: int = typer.Argument(..., help="Application attempt ID."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
) -> None:
    """Show one persisted application attempt with its audit JSON."""
    loaded_settings = load_settings(settings)
    init_database(loaded_settings.storage.database_url)

    with session_scope(loaded_settings.storage.database_url) as session:
        record = get_application_attempt_record(session, attempt_id)

    if record is None:
        typer.echo(f"Application attempt not found: {attempt_id}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Application attempt #{record.id}")
    typer.echo(f"Job ID: {record.job_id}")
    typer.echo(f"Status: {record.status}")
    typer.echo(f"Review required: {record.review_required}")
    typer.echo(f"Submitted at: {record.submitted_at.isoformat() if record.submitted_at else '<not submitted>'}")
    typer.echo(f"Created at: {record.created_at.isoformat()}")
    typer.echo("Result:")
    payload = json.loads(record.result_json or "{}")
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _copy_example(source: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        typer.echo(f"Skipped existing file: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    typer.echo(f"Created {destination}")


def _collect_review_edits(draft, interactive: bool) -> dict[str, str]:
    if not interactive:
        return {}

    edits: dict[str, str] = {}
    for field in draft.fields:
        if not field.requires_human_review or field.input_type == FieldInputType.FILE:
            continue

        current = field.proposed_value or ""
        typer.echo("")
        typer.echo(f"Review field: {field.label}")
        typer.echo(f"Reason: {field.reason}")
        typer.echo(f"Current value: {current or '<empty>'}")
        value = typer.prompt(
            "New value (leave blank to keep pending)",
            default="",
            show_default=False,
        )
        if value.strip():
            edits[field.field_id] = value.strip()

    return edits


async def _search_jobs(settings, keyword: str, limit: int):
    adapters = get_enabled_source_adapters(settings)
    effective_limit = min(limit, settings.runtime.max_jobs_per_source)
    all_jobs = []
    for adapter in adapters:
        all_jobs.extend(await adapter.search(keyword=keyword, limit=effective_limit))
    return all_jobs[:effective_limit]


def _rank_persisted_jobs(settings, profile, keyword: str) -> int:
    client = create_llm_client(settings.llm)
    with session_scope(settings.storage.database_url) as session:
        job_records = list_job_posting_records(session)
        jobs = [job_from_record(record) for record in job_records]
        evaluations: dict[str, CompatibilityEvaluation] = {}
        for job in jobs:
            evaluation = client.complete_model(
                _compatibility_prompt(profile, job, keyword),
                CompatibilityEvaluation,
            )
            evaluations[job.url] = evaluation

        matches = rank_jobs(jobs, profile, keyword, evaluations)
        records_by_url = {record.url: record for record in job_records}
        for match in matches:
            matching_record = records_by_url[match.job.url]
            save_job_match(session, matching_record, match)
        return len(matches)


def _compatibility_prompt(profile, job, keyword: str) -> str:
    return json.dumps(
        {
            "profile": profile.model_dump(mode="json"),
            "job": job.model_dump(mode="json"),
            "keyword": keyword,
        }
    )


def _local_form_job(url: str) -> JobPosting:
    return JobPosting(
        source="local_form",
        url=url,
        title="Local form review",
        company="Scrap Master",
        location="local",
        remote_type=RemoteType.UNKNOWN,
        seniority=Seniority.UNKNOWN,
        contract_type=ContractType.UNKNOWN,
        description="Local fake form used to create a human review draft.",
        requirements=[],
    )
