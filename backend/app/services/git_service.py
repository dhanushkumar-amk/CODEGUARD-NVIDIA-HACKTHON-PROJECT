"""
Git Service: Handles repository cloning, validation, file discovery, and cleanup.
Uses GitPython with shallow clones and safe temporary directory lifecycle management.
"""
import json
import logging
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import git
import httpx

logger = logging.getLogger(__name__)

# Extensions considered relevant for accessibility auditing
FRONTEND_EXTENSIONS = {".jsx", ".tsx", ".js", ".ts", ".html", ".vue", ".svelte"}

# Directories to exclude from file tree scans
EXCLUDE_DIRS = {
    "node_modules",
    "dist",
    "build",
    ".git",
    ".next",
    ".nuxt",
    ".output",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    "vendor",
    ".github",
    ".vscode",
}

# Maximum files to index for demo purposes
MAX_SCANNABLE_FILES = 100

# Maximum repository size limit in KB (200MB = 204,800 KB)
MAX_REPO_SIZE_KB = 200 * 1024


# -------------------------------------------------------------------------
# Custom Exceptions
# -------------------------------------------------------------------------

class GitServiceError(Exception):
    """Base exception for Git operations."""
    pass


class InvalidRepoUrlError(GitServiceError):
    """Raised when repository URL is malformed or from an unsupported provider."""
    pass


class RepoTooLargeError(GitServiceError):
    """Raised when repository exceeds the maximum allowed size limit."""
    pass


class RepoNotFoundError(GitServiceError):
    """Raised when remote repository does not exist (404) or is private."""
    pass


class CloneFailedError(GitServiceError):
    """Raised when cloning fails due to network, git, or filesystem errors."""
    pass


# -------------------------------------------------------------------------
# Helper Functions
# -------------------------------------------------------------------------

def _remove_readonly(func, path, excinfo):
    """Clear the readonly bit and reattempt removal (fixes Windows .git deletion errors)."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception as e:
        logger.warning(f"Could not remove path {path}: {e}")


def get_scan_temp_dir(scan_id: str) -> Path:
    """Return the temporary folder path allocated for a specific scan_id."""
    return Path(tempfile.gettempdir()) / "codeguard" / scan_id


def validate_repo_url(repo_url: str) -> None:
    """
    Validate that the repository URL is a valid public GitHub, GitLab, or Bitbucket URL.
    """
    if not repo_url or not isinstance(repo_url, str):
        raise InvalidRepoUrlError("Repository URL must be a non-empty string.")

    cleaned_url = repo_url.strip()
    parsed = urlparse(cleaned_url)

    if parsed.scheme not in ("http", "https"):
        raise InvalidRepoUrlError(
            f"Invalid URL protocol '{parsed.scheme}'. Only HTTPS repository URLs are supported."
        )

    allowed_domains = {"github.com", "gitlab.com", "bitbucket.org", "www.github.com", "www.gitlab.com"}
    if parsed.netloc.lower() not in allowed_domains:
        raise InvalidRepoUrlError(
            f"Unsupported Git host '{parsed.netloc}'. Supported hosts: GitHub, GitLab, Bitbucket."
        )

    # Path must contain at least owner and repo: /owner/repo
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        raise InvalidRepoUrlError(
            f"Invalid repository path '{parsed.path}'. Expected format: https://github.com/owner/repository"
        )


def check_github_repo_size(repo_url: str) -> None:
    """
    Check repository size and accessibility via GitHub REST API before cloning.
    Fails early if repository is >200MB or does not exist.
    """
    cleaned_url = repo_url.strip()
    match = re.match(r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", cleaned_url, re.IGNORECASE)
    if not match:
        return

    owner, repo = match.group(1), match.group(2)
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    try:
        with httpx.Client(timeout=6.0, follow_redirects=True) as client:
            resp = client.get(api_url, headers={"User-Agent": "CodeGuard-Ingest/1.0"})

            if resp.status_code == 404:
                raise RepoNotFoundError(
                    f"Repository '{owner}/{repo}' not found on GitHub or is private."
                )
            elif resp.status_code == 200:
                data = resp.json()
                size_kb = data.get("size", 0)
                if size_kb > MAX_REPO_SIZE_KB:
                    raise RepoTooLargeError(
                        f"Repository size ({size_kb / 1024:.1f} MB) exceeds maximum limit of 200 MB."
                    )
            elif resp.status_code == 403:
                # Rate limited or forbidden; log and allow shallow clone to handle it
                logger.warning(f"GitHub API rate limited checking {api_url}: {resp.status_code}")
    except (RepoNotFoundError, RepoTooLargeError):
        raise
    except httpx.RequestError as exc:
        logger.warning(f"Network error querying GitHub API: {exc}. Proceeding to clone.")


# -------------------------------------------------------------------------
# Core Service Functions
# -------------------------------------------------------------------------

def clone_repo(repo_url: str, scan_id: str, branch: Optional[str] = "main") -> str:
    """
    Clones a remote repository using GitPython with depth=1 into an isolated temp directory.

    Args:
        repo_url: Remote git repository URL.
        scan_id: Unique scan job identifier.
        branch: Optional git branch to clone (defaults to 'main').

    Returns:
        Local filesystem path to cloned repository.

    Raises:
        InvalidRepoUrlError: If the repository URL is invalid.
        RepoNotFoundError: If the repository doesn't exist or is private.
        RepoTooLargeError: If the repository size exceeds 200MB.
        CloneFailedError: If the git clone operation fails.
    """
    validate_repo_url(repo_url)
    check_github_repo_size(repo_url)

    target_dir = get_scan_temp_dir(scan_id)

    # Ensure clean directory
    if target_dir.exists():
        cleanup_repo(scan_id)

    target_dir.parent.mkdir(parents=True, exist_ok=True)

    clone_kwargs: Dict[str, Any] = {
        "depth": 1,
        "single_branch": True,
    }
    import sys
    if sys.platform != "win32":
        clone_kwargs["kill_after_timeout"] = 60

    if branch:
        clone_kwargs["branch"] = branch

    try:
        logger.info(f"Cloning {repo_url} into {target_dir} (branch={branch}, depth=1)...")
        git.Repo.clone_from(url=repo_url, to_path=str(target_dir), **clone_kwargs)
        return str(target_dir)

    except git.exc.GitCommandError as exc:
        err_msg = str(exc)
        # Check if the requested branch failed, retry with default branch
        if branch and ("Remote branch" in err_msg or "not found in upstream" in err_msg):
            logger.info(f"Branch '{branch}' not found. Retrying with default branch...")
            clone_kwargs.pop("branch", None)
            try:
                git.Repo.clone_from(url=repo_url, to_path=str(target_dir), **clone_kwargs)
                return str(target_dir)
            except git.exc.GitCommandError as retry_exc:
                err_msg = str(retry_exc)

        # Cleanup failed partial clone
        cleanup_repo(scan_id)

        if "Repository not found" in err_msg or "not found" in err_msg.lower():
            raise RepoNotFoundError(f"Repository not found or is private: {repo_url}") from exc
        elif "Authentication failed" in err_msg or "could not read Username" in err_msg:
            raise RepoNotFoundError(f"Repository requires authentication or is private: {repo_url}") from exc
        else:
            raise CloneFailedError(f"Failed to clone repository: {err_msg}") from exc

    except Exception as exc:
        cleanup_repo(scan_id)
        raise CloneFailedError(f"Unexpected error cloning repository: {str(exc)}") from exc


def find_frontend_files(repo_path: str) -> List[str]:
    """
    Traverses repository path and discovers relevant frontend UI source files.

    Excludes: node_modules, build, dist, .git, test/spec files.
    Caps at MAX_SCANNABLE_FILES (100 files).

    Returns:
        List of relative file paths (e.g. 'src/App.tsx').
    """
    root_path = Path(repo_path)
    if not root_path.exists():
        return []

    frontend_files: List[str] = []

    for dirpath, dirnames, filenames in os.walk(str(root_path)):
        # Prune excluded directories in-place to prevent os.walk from descending
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS and not d.startswith(".")]

        rel_dir = os.path.relpath(dirpath, str(root_path))
        # Skip if within test folders
        if "tests" in rel_dir.lower() or "__tests__" in rel_dir.lower():
            continue

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in FRONTEND_EXTENSIONS:
                continue

            # Skip test and spec files
            lower_name = filename.lower()
            if ".test." in lower_name or ".spec." in lower_name or lower_name.endswith(".d.ts"):
                continue

            full_path = Path(dirpath) / filename
            rel_file = str(full_path.relative_to(root_path)).replace("\\", "/")
            frontend_files.append(rel_file)

            if len(frontend_files) >= MAX_SCANNABLE_FILES:
                logger.warning(
                    f"File list capped at maximum limit of {MAX_SCANNABLE_FILES} files for performance."
                )
                return sorted(frontend_files)

    return sorted(frontend_files)


def get_repo_metadata(repo_path: str) -> Dict[str, Any]:
    """
    Inspects repository files and package.json to determine framework, file counts, and size.

    Returns:
        Dictionary with framework, file_count, total_size_kb, and package_name.
    """
    root = Path(repo_path)
    framework = "Vanilla HTML/JS"
    package_name = None
    dependencies: Dict[str, str] = {}

    pkg_path = root / "package.json"
    if pkg_path.is_file():
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
                package_name = pkg_data.get("name")
                deps = {
                    **pkg_data.get("dependencies", {}),
                    **pkg_data.get("devDependencies", {}),
                }
                dependencies = deps

                if "next" in deps:
                    framework = "Next.js"
                elif "react" in deps or "react-dom" in deps:
                    framework = "React"
                elif "vue" in deps or "nuxt" in deps:
                    framework = "Vue"
                elif "svelte" in deps or "@sveltejs/kit" in deps:
                    framework = "Svelte"
                elif "@angular/core" in deps:
                    framework = "Angular"
                else:
                    framework = "Node / Web"
        except Exception as exc:
            logger.warning(f"Could not parse package.json: {exc}")

    # Calculate total size
    total_bytes = 0
    total_files = 0
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for f in filenames:
            total_files += 1
            try:
                total_bytes += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass

    return {
        "framework": framework,
        "package_name": package_name,
        "file_count": total_files,
        "total_size_kb": round(total_bytes / 1024, 2),
        "has_package_json": pkg_path.is_file(),
    }


def cleanup_repo(scan_id: str) -> None:
    """
    Safely delete the temporary clone directory for a scan_id to free disk space.
    """
    target_dir = get_scan_temp_dir(scan_id)
    if target_dir.exists():
        try:
            shutil.rmtree(str(target_dir), onerror=_remove_readonly)
            logger.info(f"Cleaned up temporary repository clone at {target_dir}")
        except Exception as exc:
            logger.warning(f"Failed to cleanly remove {target_dir}: {exc}")
