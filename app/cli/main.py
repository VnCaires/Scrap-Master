from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

import typer
from loguru import logger

from app.config.settings import load_profile, load_settings
from app.observability import configure_logging
from app.sources import MockJobSource

app = typer.Typer(
    help="AutoApply LLM foundation CLI. No real scraping or auto-submit is implemented yet."
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


@app.command("config-check")
def config_check(
    settings: Path = typer.Option(
        Path("config/settings.example.yaml"),
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
        Path("config/profile.example.yaml"),
        "--profile",
        "-p",
        help="Path to profile YAML.",
    )
) -> None:
    """Validate a user profile YAML file."""
    loaded = load_profile(profile)
    logger.info("Profile loaded for {} {}", loaded.personal.first_name, loaded.personal.last_name)
    typer.echo(f"Profile OK: {loaded.personal.first_name} {loaded.personal.last_name}")


@app.command()
def search(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Job search keyword."),
    limit: int = typer.Option(10, "--limit", "-l", min=1, help="Maximum number of jobs."),
) -> None:
    """Search jobs using the mock source only."""
    jobs = asyncio.run(MockJobSource().search(keyword=keyword, limit=limit))
    logger.info("Mock search returned {} jobs for keyword '{}'", len(jobs), keyword)
    for index, job in enumerate(jobs, start=1):
        company = f" at {job.company}" if job.company else ""
        typer.echo(f"{index}. {job.title}{company} - {job.url}")


@app.command()
def run(
    keyword: str = typer.Option(..., "--keyword", "-k", help="Job search keyword."),
    limit: int = typer.Option(10, "--limit", "-l", min=1, help="Maximum number of jobs."),
    settings: Path = typer.Option(Path("config/settings.example.yaml"), "--settings", "-s"),
) -> None:
    """Load config, run the mock search, and stop before any browser automation."""
    loaded_settings = load_settings(settings)
    effective_limit = min(limit, loaded_settings.runtime.max_jobs_per_source)
    jobs = asyncio.run(MockJobSource().search(keyword=keyword, limit=effective_limit))
    logger.info(
        "Run completed with human review required: {}",
        loaded_settings.runtime.require_human_review,
    )
    typer.echo(f"Found {len(jobs)} mock jobs. Browser automation is not implemented yet.")


def _copy_example(source: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        typer.echo(f"Skipped existing file: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    typer.echo(f"Created {destination}")
