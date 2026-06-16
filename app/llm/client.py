from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, SecretStr

from app.config.settings import LLMSettings
from app.llm.schemas import CompatibilityEvaluation, NormalizedJob


ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMError(RuntimeError):
    """Raised when an LLM call fails or returns invalid data."""


class LLMClient(ABC):
    @abstractmethod
    def complete_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON object matching the requested schema."""

    def complete_model(self, prompt: str, model_type: type[ModelT]) -> ModelT:
        data = self.complete_json(prompt, model_type.model_json_schema())
        try:
            return model_type.model_validate(data)
        except Exception as exc:
            raise LLMError(f"LLM response failed {model_type.__name__} validation") from exc


class MockLLMClient(LLMClient):
    def complete_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        schema_text = json.dumps(schema)
        if "overall_score" in schema_text:
            return CompatibilityEvaluation(
                keyword_similarity=0.8,
                skills_match=0.75,
                seniority_match=0.7,
                location_match=0.9,
                overall_score=0.78,
                matched_reasons=["Mock evaluation found relevant Python and LLM signals."],
                missing_requirements=[],
                risks=["Mock LLM result; review before using for real applications."],
                should_apply=True,
                requires_human_review=True,
            ).model_dump()

        return NormalizedJob(
            title="Normalized Mock Job",
            company=None,
            location=None,
            remote_type="unknown",
            seniority="unknown",
            contract_type="unknown",
            required_skills=["Python"],
            summary="Mock normalized job generated for local development.",
            confidence=0.8,
        ).model_dump()


class OpenAICompatibleLLMClient(LLMClient):
    def __init__(
        self,
        api_key: SecretStr,
        model: str,
        base_url: str | None = None,
        temperature: float = 0.1,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.temperature = temperature
        self.timeout = timeout

    def complete_json(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key.get_secret_value()}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "temperature": self.temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": "Return only valid JSON matching the requested schema.",
                    },
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nSchema:\n{json.dumps(schema)}",
                    },
                ],
            },
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except Exception as exc:
            raise LLMError("OpenAI-compatible LLM request failed") from exc

        if not isinstance(parsed, dict):
            raise LLMError("OpenAI-compatible LLM returned non-object JSON")
        return parsed


def create_llm_client(settings: LLMSettings) -> LLMClient:
    if settings.provider == "mock":
        return MockLLMClient()
    if settings.provider == "openai_compatible":
        if settings.api_key is None:
            raise LLMError("LLM_API_KEY is required for openai_compatible provider")
        return OpenAICompatibleLLMClient(
            api_key=settings.api_key,
            model=settings.model,
            base_url=settings.base_url,
            temperature=settings.temperature,
        )
    raise LLMError(f"unsupported LLM provider: {settings.provider}")
