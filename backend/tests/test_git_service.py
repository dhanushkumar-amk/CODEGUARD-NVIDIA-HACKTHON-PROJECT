import json
import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient
import git

from app.main import app
from app.services.git_service import (
    clone_repo,
    find_frontend_files,
    get_repo_metadata,
    cleanup_repo,
    get_scan_temp_dir,
    InvalidRepoUrlError,
    RepoNotFoundError,
)

client = TestClient(app)


@pytest.fixture
def local_git_repo(tmp_path):
    """Creates a miniature local git repository with frontend components and tests."""
    repo_dir = tmp_path / "mock-source-repo"
    repo_dir.mkdir()

    # Initialize git repo
    repo = git.Repo.init(repo_dir)

    # Add package.json
    pkg_json = {
        "name": "sample-react-app",
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
        },
    }
    (repo_dir / "package.json").write_text(json.dumps(pkg_json), encoding="utf-8")

    # Add frontend files
    src_dir = repo_dir / "src"
    src_dir.mkdir()
    (src_dir / "App.tsx").write_text("export const App = () => <h1>Hello</h1>;", encoding="utf-8")
    (src_dir / "Button.jsx").write_text("export const Button = () => <button>Click</button>;", encoding="utf-8")

    # Add files that should be ignored
    (src_dir / "App.test.tsx").write_text("test('renders', () => {});", encoding="utf-8")
    nm_dir = repo_dir / "node_modules" / "dummy"
    nm_dir.mkdir(parents=True)
    (nm_dir / "index.js").write_text("console.log('ignored');", encoding="utf-8")

    # Commit files
    repo.git.add(A=True)
    repo.index.commit("Initial commit")

    return repo_dir


def test_invalid_repo_url():
    """Verify invalid URL formats and hosts raise InvalidRepoUrlError."""
    with pytest.raises(InvalidRepoUrlError):
        clone_repo("not-a-url", scan_id="test_invalid_1")

    with pytest.raises(InvalidRepoUrlError):
        clone_repo("ftp://github.com/user/repo", scan_id="test_invalid_2")

    with pytest.raises(InvalidRepoUrlError):
        clone_repo("https://unsupported-host.com/user/repo", scan_id="test_invalid_3")

    with pytest.raises(InvalidRepoUrlError):
        clone_repo("https://github.com/just-one-segment", scan_id="test_invalid_4")


def test_nonexistent_repo():
    """Verify non-existent repository raises RepoNotFoundError."""
    non_existent = "https://github.com/octocat/definitely-not-existing-repo-xyz-987"
    with pytest.raises(RepoNotFoundError):
        clone_repo(non_existent, scan_id="test_nonexistent")


def test_find_frontend_files_and_metadata(local_git_repo):
    """Verify file discovery filters out node_modules and tests, and detects React."""
    files = find_frontend_files(str(local_git_repo))
    assert "src/App.tsx" in files
    assert "src/Button.jsx" in files
    assert not any("test" in f for f in files)
    assert not any("node_modules" in f for f in files)

    metadata = get_repo_metadata(str(local_git_repo))
    assert metadata["framework"] == "React"
    assert metadata["package_name"] == "sample-react-app"
    assert metadata["file_count"] >= 3


def test_clone_and_cleanup_lifecycle(local_git_repo):
    """Verify cloning from a local source repository and subsequent cleanup."""
    scan_id = "test_lifecycle_123"
    repo_url = f"file://{local_git_repo}"

    # Use monkeypatch or allow file:// in test for direct validation
    from unittest.mock import patch
    with patch("app.services.git_service.validate_repo_url"):
        cloned_path = clone_repo(repo_url, scan_id=scan_id, branch=None)
        assert Path(cloned_path).exists()
        assert (Path(cloned_path) / "src" / "App.tsx").exists()

        # Test cleanup
        cleanup_repo(scan_id)
        assert not get_scan_temp_dir(scan_id).exists()


def test_public_repo_clone():
    """Verify cloning a tiny public GitHub repository end-to-end."""
    scan_id = "test_public_hello"
    public_url = "https://github.com/octocat/Hello-World"

    try:
        cloned_path = clone_repo(public_url, scan_id=scan_id)
        assert Path(cloned_path).exists()

        files = find_frontend_files(cloned_path)
        assert isinstance(files, list)

        metadata = get_repo_metadata(cloned_path)
        assert "framework" in metadata
    finally:
        cleanup_repo(scan_id)
        assert not get_scan_temp_dir(scan_id).exists()


def test_api_start_scan_validation_errors():
    """Verify POST /api/scan/start returns proper HTTP error codes for invalid inputs."""
    # 400 Bad Request on invalid URL
    resp = client.post("/api/scan/start", json={"repo_url": "ftp://bad-url.com"})
    assert resp.status_code == 400
    assert "Invalid URL" in resp.json()["detail"] or "Unsupported" in resp.json()["detail"]

    # 404 Not Found on nonexistent repo
    resp = client.post("/api/scan/start", json={"repo_url": "https://github.com/octocat/missing-repo-abc-123"})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_api_start_scan_and_cleanup_public_repo():
    """Verify POST /api/scan/start clones a real public repo and DELETE cleans it up."""
    public_url = "https://github.com/octocat/Hello-World"
    resp = client.post("/api/scan/start", json={"repo_url": public_url})
    assert resp.status_code == 200

    data = resp.json()
    scan_id = data["scan_id"]
    assert scan_id.startswith("scan_")
    assert "framework" in data
    assert "file_count" in data
    assert get_scan_temp_dir(scan_id).exists()

    # Clean up via API endpoint
    del_resp = client.delete(f"/api/scan/{scan_id}")
    assert del_resp.status_code == 200
    assert not get_scan_temp_dir(scan_id).exists()
