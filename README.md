# Scrap Master

Initial Python foundation for a human-in-the-loop job application assistant.

This repository currently implements only the project base:

- Pydantic models for core domain data.
- YAML and environment-based configuration loading.
- Typer CLI entrypoint.
- Loguru logging.
- Example settings and profile files.
- SQLModel + SQLite persistence.
- Resume PDF validation, PT-BR-aware text normalization, and extraction to a local text artifact.
- Mock and OpenAI-compatible LLM clients.
- Explainable local ranking.
- Safe local Playwright form inspection.
- Safe local Playwright autofill for non-sensitive fields.
- Editable CLI review drafts with local resume upload that never submit applications.
- A mock job source for validating the flow without real scraping.

Real scraping, real-site form filling, and application submission are not
implemented yet.

The default example configuration uses `LLM_PROVIDER=mock`, so the current flow
works offline unless you explicitly switch to `openai_compatible`.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Playwright is planned as an optional browser automation dependency:

```bash
pip install -e ".[browser]"
python -m playwright install
```

## Commands

```bash
scrap-master --help
scrap-master init
scrap-master init-db --settings config/settings.yaml
scrap-master config-check --settings config/settings.yaml
scrap-master validate-profile --profile config/profile.yaml
scrap-master parse-resume --pdf data/input/resume.pdf
scrap-master parse-resume --pdf data/input/resume.pdf --output data/output/resume_parsed.txt
scrap-master search --keyword "Python LLM" --limit 5
scrap-master rank --keyword "Python LLM"
scrap-master run --keyword "Machine Learning Engineer" --limit 10
scrap-master inspect-form --url tests/fixtures/job_form.html
scrap-master fill-form --url tests/fixtures/job_form.html
scrap-master review --url tests/fixtures/job_form.html
scrap-master review --url tests/fixtures/job_form.html --decision draft
scrap-master review --url tests/fixtures/job_form.html --screenshot data/output/reviewed-form.png
scrap-master attempts
scrap-master attempt-show 1
```

The current `run` flow initializes the SQLite database, searches enabled
sources, persists deduplicated jobs, ranks them, stores matches, and stops
before any browser automation.

The current form flow only works against local/test pages. It can inspect fields,
autofill only safe fields, attach a validated local resume PDF during review,
let the CLI user edit pending values, and persist the review decision, but it
never clicks a submit button.

Application attempts can be audited from the CLI with `scrap-master attempts`
and `scrap-master attempt-show <id>`.

## Safety Defaults

The initial version keeps `require_human_review=true` and rejects
`allow_auto_submit=true`. The project should never invent profile data, bypass
site protections, or submit applications without explicit user approval.

## Tests

```bash
pytest
```
