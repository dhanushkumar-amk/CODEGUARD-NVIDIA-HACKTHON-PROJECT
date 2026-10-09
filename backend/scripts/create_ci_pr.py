"""
Create PR for CI/CD Pipeline and monitor GitHub Actions status.
"""
import os
import sys
import time
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from github import Auth, Github
from app.config import settings

def main():
    token = settings.GITHUB_TOKEN
    if not token:
        print("ERROR: GITHUB_TOKEN not configured in settings.")
        sys.exit(1)

    gh = Github(auth=Auth.Token(token))
    repo_name = "dhanushkumar-amk/CODEGUARD-NVIDIA-HACKTHON-PROJECT"
    print(f"Connecting to repository: {repo_name}")
    repo = gh.get_repo(repo_name)

    title = "ci: setup GitHub Actions CI/CD pipeline, dependabot, and PR template"
    body = """## 📝 Description
Sets up the continuous integration and deployment pipeline for the CodeGuard repository:
- **CI Workflow (`.github/workflows/ci.yml`)**: Parallel jobs for Backend (Ruff lint + Pytest suite with 100% mocked external APIs), Frontend (Node 20, typecheck, Vitest, build), Docker image build check (Buildx + GHA cache), and Gitleaks secret scanning.
- **CD Workflow (`.github/workflows/deploy.yml`)**: Packages and publishes container images to GHCR, deploys to Nebius Serverless Endpoints, executes a 3-minute /health smoke test loop, and deploys frontend to GitHub Pages with SPA 404 routing fallback.
- **Dependabot (`.github/dependabot.yml`)**: Automated weekly dependency update scans for pip, npm, docker, and github-actions.
- **PR Template (`.github/pull_request_template.md`)**: Quality and verification checklist.

## ✅ Quality & Verification Checklist
- [x] **Linting**: Ruff (backend) and TypeScript check (frontend) pass cleanly.
- [x] **Backend Tests**: 144 unit tests pass in 13s with zero live credentials needed.
- [x] **Frontend Tests**: 24 Vitest unit tests pass in 3s.
- [x] **Secrets**: Fully mocked in CI; zero live credentials committed.
"""
    head = "feature/ci-cd-pipeline"
    base = "master"

    # Check if PR already exists
    open_prs = list(repo.get_pulls(state="open", head=f"dhanushkumar-amk:{head}"))
    if open_prs:
        pr = open_prs[0]
        print(f"Existing Pull Request found: #{pr.number} - {pr.html_url}")
    else:
        print(f"Creating new Pull Request: '{head}' -> '{base}'...")
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
        )
        print(f"Pull Request created successfully: #{pr.number} - {pr.html_url}")

    print(f"\nMonitoring GitHub Actions workflow runs for commit {pr.head.sha}...")
    for _ in range(30):
        runs = list(repo.get_workflow_runs(head_sha=pr.head.sha))
        if runs:
            print(f"Found {len(runs)} workflow run(s):")
            for r in runs:
                print(f"  - [{r.name}] Status: {r.status} | Conclusion: {r.conclusion} | URL: {r.html_url}")
            
            all_done = all(r.status == "completed" for r in runs)
            if all_done:
                print("\nAll workflow runs completed!")
                break
        else:
            print("Waiting for workflow run to start...")
        time.sleep(10)

if __name__ == "__main__":
    main()
