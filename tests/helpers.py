from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
import yaml


def write_settings(tmp_path: Path) -> Path:
    write_pdf_with_text(tmp_path / "resume.pdf", "Python LLM Resume")

    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text(
        yaml.safe_dump(
            {
                "personal": {
                    "first_name": "Vinicius",
                    "last_name": "Caires",
                    "email": "email@example.com",
                    "phone": "",
                    "city": "Salvador",
                    "country": "Brazil",
                    "linkedin": "",
                    "github": "",
                    "portfolio": "",
                },
                "preferences": {
                    "target_roles": ["Python Developer"],
                    "keywords": ["Python", "LLM"],
                    "remote_only": True,
                    "relocation": False,
                    "contract_types": ["Remote"],
                    "minimum_salary": None,
                },
                "experience": {
                    "years_total": 3,
                    "seniority": "mid",
                    "skills": ["Python", "LLM", "APIs", "SQL"],
                    "languages": {"english": "intermediate"},
                },
                "answers": {
                    "work_authorization": "",
                    "salary_expectation": "",
                    "notice_period": "",
                    "cover_letter_template": "",
                },
            }
        ),
        encoding="utf-8",
    )

    settings_path = tmp_path / "settings.yaml"
    settings_path.write_text(
        yaml.safe_dump(
            {
                "llm": {
                    "provider": "mock",
                    "model": "gpt-4.1-mini",
                    "temperature": 0.1,
                    "api_key": None,
                    "base_url": None,
                },
                "runtime": {
                    "headless": False,
                    "max_jobs_per_source": 20,
                    "max_applications_per_run": 3,
                    "require_human_review": True,
                    "screenshot_on_error": True,
                },
                "storage": {
                    "database_url": f"sqlite:///{tmp_path / 'scrap_master.db'}",
                },
                "security": {
                    "allow_auto_submit": False,
                    "allowed_domains": ["jobs.example.test"],
                    "blocked_domains": [],
                },
                "sources": [
                    {"name": "mock", "enabled": True, "max_results": 20},
                ],
                "profile_path": str(profile_path),
                "resume_pdf_path": str(tmp_path / "resume.pdf"),
            }
        ),
        encoding="utf-8",
    )
    return settings_path


def write_pdf_with_text(path: Path, text: str) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    stream = DecodedStreamObject()
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("utf-8"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {
                    NameObject("/F1"): writer._add_object(
                        DictionaryObject(
                            {
                                NameObject("/Type"): NameObject("/Font"),
                                NameObject("/Subtype"): NameObject("/Type1"),
                                NameObject("/BaseFont"): NameObject("/Helvetica"),
                            }
                        )
                    )
                }
            )
        }
    )
    with path.open("wb") as handle:
        writer.write(handle)
