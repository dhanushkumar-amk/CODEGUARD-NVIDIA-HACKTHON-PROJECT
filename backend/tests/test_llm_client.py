"""
Unit tests for Nemotron Ultra client, cost guardrails, and tiered escalation.
All tests use mocked API responses with no live network calls.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.config import settings
from app.services.llm_client import (
    call_nemotron_fast,
    call_nemotron_ultra,
    call_with_escalation,
    get_cost_breakdown,
    get_scan_usage_stats,
    get_token_usage_stats,
    reset_cost_tracker,
    UltraBudgetExceededError,
)


@pytest.fixture(autouse=True)
def clean_cost_tracker():
    """Ensure in-memory cost metrics and scan usage are reset for each test."""
    reset_cost_tracker()
    yield
    reset_cost_tracker()


def _create_mock_client(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Helper to create a mocked AsyncOpenAI client returning specified text and token counts."""
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_usage = MagicMock()
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens
    mock_response = MagicMock(choices=[mock_choice], usage=mock_usage)

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.mark.asyncio
async def test_ultra_call_blocked_once_max_calls_reached():
    """Verify that Ultra calls are blocked once ULTRA_MAX_CALLS_PER_SCAN is reached."""
    mock_client = _create_mock_client("Reasoning patch analysis", prompt_tokens=20, completion_tokens=20)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "mock-key"), \
         patch.object(settings, "ULTRA_ENABLED", True), \
         patch.object(settings, "ULTRA_MAX_CALLS_PER_SCAN", 2), \
         patch.object(settings, "ULTRA_BUDGET_USD_PER_SCAN", 10.0), \
         patch("app.services.llm_client.get_client", return_value=mock_client):

        scan_id = "test-scan-call-limit"

        # Call 1: succeeds
        res1 = await call_nemotron_ultra("Check 1", scan_id=scan_id)
        assert res1 == "Reasoning patch analysis"

        # Call 2: succeeds
        res2 = await call_nemotron_ultra("Check 2", scan_id=scan_id)
        assert res2 == "Reasoning patch analysis"

        # Call 3: should be blocked by ULTRA_MAX_CALLS_PER_SCAN limit (2)
        with pytest.raises(UltraBudgetExceededError) as exc_info:
            await call_nemotron_ultra("Check 3", scan_id=scan_id)

        assert "call limit (2) reached" in str(exc_info.value)
        scan_stats = get_scan_usage_stats(scan_id)
        assert scan_stats["ultra_calls"] == 2


@pytest.mark.asyncio
async def test_ultra_call_blocked_once_budget_exceeded():
    """Verify that Ultra calls are blocked once the per-scan budget is exceeded."""
    # 2000 prompt tokens * $1.00/1M = $0.002
    # 2000 completion tokens * $3.00/1M = $0.006
    # Total call cost = $0.008
    mock_client = _create_mock_client("Deep diagnosis", prompt_tokens=2000, completion_tokens=2000)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "mock-key"), \
         patch.object(settings, "ULTRA_ENABLED", True), \
         patch.object(settings, "ULTRA_MAX_CALLS_PER_SCAN", 10), \
         patch.object(settings, "ULTRA_BUDGET_USD_PER_SCAN", 0.005), \
         patch("app.services.llm_client.get_client", return_value=mock_client):

        scan_id = "test-scan-budget-limit"

        # First call incurs $0.008 spend, which exceeds the $0.005 budget
        res1 = await call_nemotron_ultra("Reasoning step 1", scan_id=scan_id)
        assert res1 == "Deep diagnosis"

        # Second call must be blocked since accumulated spend ($0.008) >= budget ($0.005)
        with pytest.raises(UltraBudgetExceededError) as exc_info:
            await call_nemotron_ultra("Reasoning step 2", scan_id=scan_id)

        assert "budget limit ($0.0050) exceeded" in str(exc_info.value)


@pytest.mark.asyncio
async def test_escalation_falls_back_gracefully_when_ultra_disabled():
    """Verify that tiered escalation falls back gracefully to the fast model's result when Ultra is disabled."""
    mock_client = _create_mock_client("Fast baseline response", prompt_tokens=50, completion_tokens=50)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "mock-key"), \
         patch.object(settings, "ULTRA_ENABLED", False), \
         patch("app.services.llm_client.get_client", return_value=mock_client):

        scan_id = "test-scan-fallback"

        # Quality check deliberately returns False to trigger escalation
        def failing_quality_check(output: str) -> bool:
            return False

        # Escalation attempts Ultra, discovers ULTRA_ENABLED is False, and returns fast result without crashing
        result = await call_with_escalation(
            prompt="Analyze accessibility",
            scan_id=scan_id,
            quality_check=failing_quality_check,
        )

        assert result == "Fast baseline response"


@pytest.mark.asyncio
async def test_cost_calculation_correct_for_known_token_counts():
    """Verify that cost calculations match the exact pricing models for both Ultra and Fast tiers."""
    # Test Ultra pricing:
    # 500,000 prompt tokens @ $1.00/1M = $0.50
    # 100,000 completion tokens @ $3.00/1M = $0.30
    # Expected Ultra call cost = $0.80
    mock_ultra_client = _create_mock_client("Ultra response", prompt_tokens=500_000, completion_tokens=100_000)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "mock-key"), \
         patch.object(settings, "ULTRA_ENABLED", True), \
         patch.object(settings, "ULTRA_MAX_CALLS_PER_SCAN", 10), \
         patch.object(settings, "ULTRA_BUDGET_USD_PER_SCAN", 5.0), \
         patch("app.services.llm_client.get_client", return_value=mock_ultra_client):

        await call_nemotron_ultra("Ultra prompt", scan_id="cost-calc-scan")

    breakdown_after_ultra = get_cost_breakdown()
    assert breakdown_after_ultra["ultra_cost"] == 0.80
    assert breakdown_after_ultra["fast_cost"] == 0.00
    assert breakdown_after_ultra["total"] == 0.80

    # Test Fast pricing:
    # 1,000,000 prompt tokens @ $0.06/1M = $0.06
    # 1,000,000 completion tokens @ $0.24/1M = $0.24
    # Expected Fast call cost = $0.30
    mock_fast_client = _create_mock_client("Fast response", prompt_tokens=1_000_000, completion_tokens=1_000_000)

    with patch.object(settings, "NEBIUS_TOKEN_FACTORY_API_KEY", "mock-key"), \
         patch("app.services.llm_client.get_client", return_value=mock_fast_client):

        await call_nemotron_fast("Fast prompt", scan_id="cost-calc-scan")

    final_breakdown = get_cost_breakdown()
    assert final_breakdown["fast_cost"] == 0.30
    assert final_breakdown["ultra_cost"] == 0.80
    assert final_breakdown["total"] == 1.10

    stats = get_token_usage_stats()
    assert stats["ultra_input_tokens"] == 500_000
    assert stats["ultra_output_tokens"] == 100_000
    assert stats["fast_input_tokens"] == 1_000_000
    assert stats["fast_output_tokens"] == 1_000_000
    assert stats["total_tokens"] == 2_600_000
    assert stats["total_calls"] == 2
    assert stats["ultra_calls"] == 1
    assert stats["fast_calls"] == 1
