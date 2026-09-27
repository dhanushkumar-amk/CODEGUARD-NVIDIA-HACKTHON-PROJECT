from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.services.llm_client import (
    call_nemotron,
    LLMAuthenticationError,
    LLMTimeoutError,
    LLMRateLimitError,
)
import openai

client = TestClient(app)


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
    # Create fake request for APITimeoutError
    mock_request = MagicMock()
    mock_openai_client.chat.completions.create = AsyncMock(
        side_effect=openai.APITimeoutError(request=mock_request)
    )

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "real-key-123"):
        with patch("app.services.llm_client.get_client", return_value=mock_openai_client):
            with pytest.raises(LLMTimeoutError):
                await call_nemotron(model_id="test-model", prompt="Hello")


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
