from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.llm_client import (
    call_nemotron,
    call_nemotron_fast,
    get_total_cost_so_far,
    get_token_usage_stats,
    reset_cost_tracker,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMRateLimitError,
)
import openai

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_cost_tracker():
    """Ensure in-memory cost metrics are reset before and after each test."""
    reset_cost_tracker()
    yield
    reset_cost_tracker()


@pytest.mark.asyncio
async def test_call_nemotron_missing_key():
    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", ""):
        with pytest.raises(LLMAuthenticationError):
            await call_nemotron(model_id="test-model", prompt="Hello")


@pytest.mark.asyncio
async def test_call_nemotron_success():
    mock_choice = MagicMock()
    mock_choice.message.content = "Nemotron response"
    mock_response = MagicMock(choices=[mock_choice])

    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "real-key-123"):
        with patch("app.services.llm_client.get_client", return_value=mock_openai_client):
            res = await call_nemotron(model_id="test-model", prompt="Hello")
            assert res == "Nemotron response"


@pytest.mark.asyncio
async def test_call_nemotron_timeout_mapping():
    mock_openai_client = MagicMock()
    mock_request = MagicMock()
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=openai.APITimeoutError(request=mock_request)
    )

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "real-key-123"):
        with patch("app.services.llm_client.get_client", return_value=mock_openai_client):
            with pytest.raises(LLMTimeoutError):
                await call_nemotron(model_id="test-model", prompt="Hello")


@pytest.mark.asyncio
async def test_call_nemotron_fast_success_and_cost_tracking():
    mock_choice = MagicMock()
    mock_choice.message.content = '{"has_violation": true, "type": "image-alt"}'
    
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = 100
    mock_usage.completion_tokens = 50
    mock_response = MagicMock(choices=[mock_choice], usage=mock_usage)

    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "real-key-123"):
        with patch("app.services.llm_client.get_client", return_value=mock_openai_client):
            res = await call_nemotron_fast(
                prompt="Check <img src='test.png' />",
                response_format="json",
            )
            assert 'has_violation' in res
            
            # Check cost calculation:
            # 100 * 0.06 / 1_000_000 = 0.000006
            # 50 * 0.24 / 1_000_000 = 0.000012
            # Total = 0.000018
            cost = get_total_cost_so_far()
            assert cost == 0.000018

            stats = get_token_usage_stats()
            assert stats["total_input_tokens"] == 100
            assert stats["total_output_tokens"] == 50
            assert stats["total_calls"] == 1


def test_test_llm_ultra_route():
    with patch("app.routers.test_llm.call_nemotron", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Hello from Ultra"
        response = client.get("/test-llm/ultra")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["response"] == "Hello from Ultra"


def test_test_llm_nano_route():
    with patch("app.routers.test_llm.call_nemotron", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Hello from Nano"
        response = client.get("/test-llm/nano")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["response"] == "Hello from Nano"


def test_test_llm_fast_route():
    with patch("app.routers.test_llm.call_nemotron_fast", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "Missing alt attribute detected on image"
        response = client.get("/test-llm/fast")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "response" in data
        assert "usage" in data
        assert "total_cost_so_far" in data


def test_test_llm_cost_route():
    response = client.get("/test-llm/cost")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "total_cost_so_far" in data
    assert "stats" in data
