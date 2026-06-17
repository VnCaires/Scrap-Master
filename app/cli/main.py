from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import typer
from loguru import logger

from app.browser import BrowserAutomationError, inspect_form_page
from app.config.settings import load_profile, load_settings
from app.core.models import ContractType, JobPosting, RemoteType, Seniority
from app.documents import ResumeError, parse_resume_pdf
from app.forms import map_form_fields
from app.llm import CompatibilityEvaluation, create_llm_client
from app.observability import configure_logging
from app.ranking import rank_jobs
from app.review import build_review_draft, normalize_review_decision, render_review_draft
from app.security import mask_email, mask_name
from app.sources import get_enabled_source_adapters
from app.storage import (
    init_database,
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
) -> None:
    """Validate and extract text from a resume PDF."""
    try:
        parsed = parse_resume_pdf(pdf, max_size_mb=max_size_mb)
    except ResumeError as exc:
        logger.warning("Resume parsing failed: {}", exc)
        typer.echo(f"Resume error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    logger.info("Resume parsed: {} pages, {} bytes", parsed.page_count, parsed.size_bytes)
    typer.echo(
        f"Resume OK: {parsed.page_count} page(s), {parsed.size_bytes} bytes, "
        f"{len(parsed.text)} extracted characters"
    )


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


@app.command()
def review(
    url: str = typer.Option(..., "--url", help="Local HTML file or URL to review."),
    profile: Path | None = typer.Option(None, "--profile", "-p", help="Path to profile YAML."),
    settings: Path = typer.Option(Path("config/settings.yaml"), "--settings", "-s"),
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

    chosen = decision or typer.prompt("Decision [approve/skip/draft]", default="draft")
    try:
        status = normalize_review_decision(chosen)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

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
                "fields": [field.model_dump(mode="json") for field in mapping.fields],
                "risks": mapping.risks,
            },
        )

    typer.echo(
        f"Saved application attempt {attempt.id} with status {status.value}. "
        "No submit action was performed."
    )


def _copy_example(source: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        typer.echo(f"Skipped existing file: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    typer.echo(f"Created {destination}")


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
