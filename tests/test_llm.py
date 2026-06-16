import pytest
from pydantic import BaseModel

from app.llm import CompatibilityEvaluation, LLMError, MockLLMClient


class ImpossibleSchema(BaseModel):
    required_value: int


def test_mock_llm_returns_valid_compatibility_model() -> None:
    client = MockLLMClient()

    evaluation = client.complete_model("{}", CompatibilityEvaluation)

    assert evaluation.overall_score > 0
    assert evaluation.requires_human_review is True


def test_llm_model_validation_failure_is_wrapped() -> None:
    client = MockLLMClient()

    with pytest.raises(LLMError):
        client.complete_model("{}", ImpossibleSchema)
