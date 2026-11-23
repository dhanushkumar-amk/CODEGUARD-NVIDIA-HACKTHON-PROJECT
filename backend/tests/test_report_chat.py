import json
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ScanReport, Violation
from app.routers import report as report_router
from app.services import report_chat_service


@pytest.fixture
def report_chat(monkeypatch):
    report = ScanReport(
        scan_id="test-chat",
        repo_url="https://github.com/example/shop",
        violations=[
            Violation(
                id="checkout-keyboard",
                file="src/Checkout.tsx",
                line=42,
                type="keyboard-trap",
                description="Keyboard focus cannot leave the checkout dialog.",
            ),
        ],
    )
    scan = {"status": "completed", "report": report}
    model = AsyncMock(return_value='{"answer":"Focus is trapped in checkout.","evidence_ids":[1]}')
    monkeypatch.setattr(report_router, "get_scan", lambda scan_id: scan if scan_id == report.scan_id else None)
    monkeypatch.setattr(report_chat_service, "call_nemotron_fast", model)
    return TestClient(app), scan, model


def test_chat_returns_server_sourced_evidence(report_chat):
    client, _, model = report_chat
    response = client.post("/api/report/test-chat/chat", json={
        "question": "Which line causes it?",
        "previous_questions": ["Why is checkout hard to use with a keyboard?"],
    })

    assert response.status_code == 200
    assert response.json() == {
        "answer": "Focus is trapped in checkout.",
        "citations": [{
            "violation_id": "checkout-keyboard",
            "file": "src/Checkout.tsx",
            "line": 42,
            "rule": "keyboard-trap",
            "description": "Keyboard focus cannot leave the checkout dialog.",
            "verification_status": None,
        }],
    }
    prompt = json.loads(model.await_args.args[0])
    assert prompt["report"]["findings"][0]["file"] == "src/Checkout.tsx"
    assert prompt["previous_questions"] == ["Why is checkout hard to use with a keyboard?"]


def test_chat_rejects_invented_evidence(report_chat):
    client, _, model = report_chat
    model.return_value = '{"answer":"Unsupported response.","evidence_ids":[99]}'
    assert client.post("/api/report/test-chat/chat", json={"question": "Any issues?"}).status_code == 502


def test_chat_handles_missing_evidence(report_chat):
    client, _, model = report_chat
    model.return_value = '{"answer":null,"evidence_ids":[]}'
    response = client.post("/api/report/test-chat/chat", json={"question": "Was search tested?"})

    assert response.status_code == 200
    assert "enough evidence" in response.json()["answer"]
    assert response.json()["citations"] == []


def test_chat_validates_report_and_question_before_calling_model(report_chat):
    client, scan, model = report_chat
    assert client.post("/api/report/missing/chat", json={"question": "Any issues?"}).status_code == 404
    assert client.post("/api/report/test-chat/chat", json={"question": "  "}).status_code == 422
    scan["status"] = "scanning"
    assert client.post("/api/report/test-chat/chat", json={"question": "Any issues?"}).status_code == 409
    model.assert_not_awaited()


def test_chat_handles_unavailable_model(report_chat):
    client, _, model = report_chat
    model.side_effect = report_router.LLMClientError("Provider error")
    response = client.post("/api/report/test-chat/chat", json={"question": "What failed?"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Report chat is temporarily unavailable."
