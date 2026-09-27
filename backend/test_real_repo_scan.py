"""
Verification script: runs scanner against a real remote repository and prints the resulting scan batch.
"""
import json
import os
import sys

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.services.git_service import clone_repo, find_frontend_files, get_repo_metadata, cleanup_repo
from app.services.scanner_service import prepare_scan_batch

TEST_REPOS = [
    "https://github.com/octocat/Spoon-Knife",
    "https://github.com/mdn/todo-react",
]

def run_verification():
    for repo_url in TEST_REPOS:
        scan_id = "test_" + repo_url.split("/")[-1].replace("-", "_")
        print("=" * 70)
        print(f"CODEGUARD SCANNER VERIFICATION: {repo_url}")
        print("=" * 70)

        try:
            # 1. Clone repository
            print(f"\n[1] Cloning repository with shallow clone (depth=1)...")
            repo_path = clone_repo(repo_url, scan_id)
            print(f"    Cloned to: {repo_path}")

            # 2. Discover frontend files
            print(f"\n[2] Discovering scannable frontend files...")
            files = find_frontend_files(repo_path)
            print(f"    Found {len(files)} frontend files: {files}")

            # 3. Detect metadata
            metadata = get_repo_metadata(repo_path)
            print(f"    Detected framework: {metadata.get('framework', 'Vanilla HTML/JS')}")

            # 4. Prepare scan batches
            print(f"\n[3] Running prepare_scan_batch (safe read -> markup isolation -> chunking)...")
            batch = prepare_scan_batch(repo_path, files)
            print(f"    Total scan chunks prepared: {len(batch)}")

            # 5. Print summary table and details
            print("\n" + "=" * 70)
            print(f"{'FILE NAME':<35} | {'CHUNK #':<8} | {'EST. TOKENS':<12}")
            print("-" * 70)
            total_tokens = 0
            for item in batch:
                total_tokens += item['estimated_tokens']
                print(f"{item['file']:<35} | {item['chunk_index']:<8} | {item['estimated_tokens']:<12}")

            print("-" * 70)
            print(f"TOTAL ESTIMATED TOKENS ACROSS ALL CHUNKS: {total_tokens}")
            print("=" * 70)

            # Print preview of the extracted content
            if batch:
                print("\n[SAMPLE EXTRACTED CHUNK PREVIEW]")
                sample = batch[0]
                print(f"File: {sample['file']} (Chunk {sample['chunk_index']})")
                print("-" * 40)
                preview = sample['content'][:300] + ("..." if len(sample['content']) > 300 else "")
                print(preview)
                print("-" * 40)

        finally:
            print(f"\n[4] Cleaning up cloned test repository {scan_id}...")
            cleanup_repo(scan_id)
            print("    Cleanup complete.\n")

    return True

if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
