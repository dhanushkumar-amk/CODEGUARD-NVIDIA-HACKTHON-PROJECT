"""
Unit and integration tests for github_service.py and POST /api/report/{scan_id}/create-pr endpoint.
"""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient
from github import GithubException

from app.main import app
from app.models.schemas import ProposedFix, UnifiedViolationRecord, DiagnosedViolation
from app.services.github_service import (
    parse_github_repo,
    get_github_client,
    create_remediation_branch,
    commit_verified_fixes,
    open_pull_request,
    create_remediation_pr,
)
from app.state import scans, generate_mock_scan_data

client = TestClient(app)


def test_parse_github_repo_valid_formats():
    # HTTPS with .git
    owner, repo = parse_github_repo("https://github.com/dhanushkumar-amk/demo-app.git")
    assert owner == "dhanushkumar-amk"
    assert repo == "demo-app"

    # HTTPS without .git
    owner, repo = parse_github_repo("https://github.com/dhanushkumar-amk/CODEGUARD-PROJECT")
    assert owner == "dhanushkumar-amk"
    assert repo == "CODEGUARD-PROJECT"

    # SSH format
    owner, repo = parse_github_repo("git@github.com:octocat/Hello-World.git")
    assert owner == "octocat"
    assert repo == "Hello-World"

    # Slug format
    owner, repo = parse_github_repo("octocat/Spoon-Knife")
    assert owner == "octocat"
    assert repo == "Spoon-Knife"


def test_parse_github_repo_invalid():
    with pytest.raises(ValueError, match="Could not parse GitHub repository"):
        parse_github_repo("not-a-valid-repo")


def test_get_github_client_missing_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.GITHUB_TOKEN", "")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GitHub Personal Access Token is not configured"):
        get_github_client()


def test_create_remediation_branch_success():
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_branch = MagicMock()
    mock_branch.commit.sha = "abc123sha"
    mock_repo.default_branch = "main"

    # First call: get_branch("main") -> base branch exists
    # Second call: get_branch("codeguard-fixes-12345678") -> 404 (doesn't exist yet)
    def branch_side_effect(name):
        if name == "main":
            return mock_branch
        raise GithubException(status=404, data={"message": "Not Found"})

    mock_repo.get_branch.side_effect = branch_side_effect
    mock_gh.get_repo.return_value = mock_repo

    branch_name = create_remediation_branch(
        repo_owner="test-owner",
        repo_name="test-repo",
        base_branch="main",
        scan_id="scan_12345678abcdef",
        client=mock_gh,
    )

    assert branch_name == "codeguard-fixes-12345678"
    mock_repo.create_git_ref.assert_called_once_with(
        ref="refs/heads/codeguard-fixes-12345678",
        sha="abc123sha",
    )


def test_create_remediation_branch_already_exists():
    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_repo.default_branch = "main"
    mock_repo.get_branch.return_value = MagicMock()  # Returns existing branch

    mock_gh.get_repo.return_value = mock_repo

    with pytest.raises(ValueError, match="already exists"):
        create_remediation_branch(
            repo_owner="test-owner",
            repo_name="test-repo",
            base_branch="main",
            scan_id="scan_12345678",
            client=mock_gh,
        )


def test_commit_verified_fixes_updates_file():
    scan_id = "scan_test_commit"
    scans[scan_id] = generate_mock_scan_data(scan_id, repo_url="https://github.com/test-owner/test-repo")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_content_file = MagicMock()
    mock_content_file.path = "src/components/Header.tsx"
    mock_content_file.sha = "file_sha_123"
    # Content matching mock fix_01
    mock_content_file.decoded_content = b'<button className="text-slate-400 bg-slate-900">Submit</button>'

    mock_repo.get_contents.return_value = mock_content_file
    mock_gh.get_repo.return_value = mock_repo

    files_changed = commit_verified_fixes(
        repo_owner="test-owner",
        repo_name="test-repo",
        branch_name="codeguard-fixes-test",
        scan_id=scan_id,
        client=mock_gh,
    )

    assert files_changed >= 1
    mock_repo.update_file.assert_called()


def test_open_pull_request_success():
    scan_id = "scan_test_pr"
    scans[scan_id] = generate_mock_scan_data(scan_id, repo_url="https://github.com/test-owner/test-repo")

    mock_gh = MagicMock()
    mock_repo = MagicMock()
    mock_repo.default_branch = "main"

    mock_pr = MagicMock()
    mock_pr.html_url = "https://github.com/test-owner/test-repo/pull/1"
    mock_pr.number = 1
    mock_repo.create_pull.return_value = mock_pr
    mock_gh.get_repo.return_value = mock_repo

    pr_url = open_pull_request(
        repo_owner="test-owner",
        repo_name="test-repo",
        branch_name="codeguard-fixes-test",
        base_branch="main",
        scan_id=scan_id,
        client=mock_gh,
    )

    assert pr_url == "https://github.com/test-owner/test-repo/pull/1"
    mock_repo.create_pull.assert_called_once()
    call_kwargs = mock_repo.create_pull.call_args[1]
    assert "CodeGuard:" in call_kwargs["title"]
    assert "verified accessibility" in call_kwargs["title"]
    assert call_kwargs["head"] == "codeguard-fixes-test"
    assert call_kwargs["base"] == "main"


def test_create_remediation_pr_missing_token(monkeypatch):
    monkeypatch.setattr("app.config.settings.GITHUB_TOKEN", "")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    result = create_remediation_pr("https://github.com/test-owner/test-repo", "scan_123")
    assert result["status"] == "failed"
    assert "GitHub Personal Access Token is not configured" in result["error"]


def test_create_remediation_pr_no_write_access():
    with patch("app.services.github_service.get_github_client") as mock_get_client:
        mock_gh = MagicMock()
        mock_gh.get_repo.side_effect = GithubException(status=403, data={"message": "Must have push access"})
        mock_get_client.return_value = mock_gh

        result = create_remediation_pr("https://github.com/some-user/public-repo", "scan_123")
        assert result["status"] == "failed"
        assert "No write access" in result["error"]


def test_create_remediation_pr_orchestration_success():
    scan_id = "scan_orch_success"
    scans[scan_id] = generate_mock_scan_data(scan_id, repo_url="https://github.com/test-owner/test-repo")

    with patch("app.services.github_service.get_github_client") as mock_get_client, \
         patch("app.services.github_service.create_remediation_branch", return_value="codeguard-fixes-orch"), \
         patch("app.services.github_service.commit_verified_fixes", return_value=3), \
         patch("app.services.github_service.open_pull_request", return_value="https://github.com/test-owner/test-repo/pull/99"):

        mock_repo = MagicMock()
        mock_repo.default_branch = "main"
        mock_gh = MagicMock()
        mock_gh.get_repo.return_value = mock_repo
        mock_get_client.return_value = mock_gh

        result = create_remediation_pr("https://github.com/test-owner/test-repo", scan_id)
        assert result["status"] == "success"
        assert result["pr_url"] == "https://github.com/test-owner/test-repo/pull/99"
        assert result["files_changed"] == 3


def test_endpoint_create_pr_success():
    scan_id = "scan_endpoint_test"
    scans[scan_id] = generate_mock_scan_data(scan_id, repo_url="https://github.com/test-owner/test-repo")

    with patch("app.services.github_service.create_remediation_pr") as mock_create_pr:
        mock_create_pr.return_value = {
            "status": "success",
            "pr_url": "https://github.com/test-owner/test-repo/pull/123",
            "files_changed": 4,
        }

        response = client.post(
            f"/api/report/{scan_id}/create-pr",
            json={"repo_url": "https://github.com/test-owner/test-repo"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["pr_url"] == "https://github.com/test-owner/test-repo/pull/123"
        assert data["files_changed"] == 4
        mock_create_pr.assert_called_once_with(
            repo_url="https://github.com/test-owner/test-repo",
            scan_id=scan_id,
        )


def test_endpoint_create_pr_failure_graceful():
    scan_id = "scan_endpoint_fail"
    scans[scan_id] = generate_mock_scan_data(scan_id, repo_url="https://github.com/foreign/repo")

    with patch("app.services.github_service.create_remediation_pr") as mock_create_pr:
        mock_create_pr.return_value = {
            "status": "failed",
            "error": "No write access to repository 'foreign/repo'.",
        }

        response = client.post(f"/api/report/{scan_id}/create-pr")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert "No write access" in data["error"]
