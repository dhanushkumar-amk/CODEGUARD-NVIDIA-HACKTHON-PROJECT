import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import ProposedFix, ScanReport, VerificationResult

client = TestClient(app)


def test_health_endpoint():
    """Verify /health returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_start_scan_endpoint():
    """Verify POST /api/scan/start initiates a scan and returns a scan_id."""
    from unittest.mock import patch
    payload = {
        "repo_url": "https://github.com/octocat/Hello-World",
        "branch": "main",
    }
    with patch("app.routers.scan.clone_repo", return_value="/tmp/mock/path"), \
         patch("app.routers.scan.find_frontend_files", return_value=["src/App.tsx"]), \
         patch("app.routers.scan.get_repo_metadata", return_value={"framework": "React"}):
        response = client.post("/api/scan/start", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data
        assert data["scan_id"].startswith("scan_")
        assert data["status"] == "queued"
        assert data["framework"] == "React"
        assert data["file_count"] == 1


def test_get_scan_status_endpoint():
    """Verify GET /api/scan/{scan_id} returns metadata and progress."""
    response = client.get("/api/scan/scan_test123")
    assert response.status_code == 200
    data = response.json()
    assert data["scan_id"] == "scan_test123"
    assert "status" in data
    assert "progress" in data


def test_get_fixes_endpoint():
    """Verify GET /api/fix/{scan_id} returns a list of ProposedFix models."""
    response = client.get("/api/fix/scan_test123")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Validate against Pydantic schema
    first_fix = ProposedFix(**data[0])
    assert first_fix.violation_id is not None
    assert first_fix.diff is not None
    assert first_fix.explanation is not None


def test_get_verification_endpoint():
    """Verify GET /api/verify/{scan_id} returns a list of VerificationResult models."""
    response = client.get("/api/verify/scan_test123")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Validate against Pydantic schema
    first_res = VerificationResult(**data[0])
    assert first_res.fix_id is not None
    assert first_res.verified is True
    assert first_res.tests_passed is True


def test_get_report_endpoint():
    """Verify GET /api/report/{scan_id} returns a valid ScanReport model."""
    response = client.get("/api/report/scan_test123")
    assert response.status_code == 200
    data = response.json()
    # Validate against Pydantic schema
    report = ScanReport(**data)
    assert report.scan_id == "scan_test123"
    assert len(report.violations) > 0
    assert len(report.fixes) > 0
    assert len(report.verification_results) > 0
    assert report.overall_score_before <= report.overall_score_after


def test_websocket_progress_stream():
    """Verify WS /ws/{scan_id} accepts connection and streams mock pipeline stages."""
    scan_id = "scan_stream_test"
    with client.websocket_connect(f"/ws/{scan_id}") as websocket:
        # Message 1: init
        msg1 = websocket.receive_json()
        assert msg1["stage"] == "init"
        assert msg1["progress"] == 5
        assert "scan request" in msg1["message"].lower()

        # Message 2: cloning
        msg2 = websocket.receive_json()
        assert msg2["stage"] == "cloning"
        assert msg2["progress"] == 15

        # Message 3: preparing
        msg3 = websocket.receive_json()
        assert msg3["stage"] == "preparing"
        assert msg3["progress"] >= 20
        assert "Parsed" in msg3["message"]


def test_global_exception_handler():
    """Verify unhandled exceptions produce clean JSON with status 500 without crashing."""
    @app.get("/api/test-error")
    def trigger_error():
        raise ValueError("Simulated unexpected crash")

    # Use raise_server_exceptions=False to test Starlette/FastAPI's JSON error response
    safe_client = TestClient(app, raise_server_exceptions=False)
    response = safe_client.get("/api/test-error")
    assert response.status_code == 500
    data = response.json()
    assert data["status_code"] == 500
    assert data["error"] == "Internal Server Error"
    assert "Simulated unexpected crash" in data["detail"]
