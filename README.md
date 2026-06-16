# AutoApply LLM

Initial Python foundation for a human-in-the-loop job application assistant.

This repository currently implements only the project base:

- Pydantic models for core domain data.
- YAML and environment-based configuration loading.
- Typer CLI entrypoint.
- Loguru logging.
- Example settings and profile files.
- A mock job source for validating the flow without real scraping.

Real scraping, browser automation, form filling, and application submission are
not implemented yet.

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
autoapply --help
autoapply init
autoapply config-check --settings config/settings.example.yaml
autoapply validate-profile --profile config/profile.example.yaml
autoapply search --keyword "Python LLM" --limit 5
autoapply run --keyword "Machine Learning Engineer" --limit 10
```

## Safety Defaults

The initial version keeps `require_human_review=true` and rejects
`allow_auto_submit=true`. The project should never invent profile data, bypass
site protections, or submit applications without explicit user approval.

## Tests

```bash
pytest
```
