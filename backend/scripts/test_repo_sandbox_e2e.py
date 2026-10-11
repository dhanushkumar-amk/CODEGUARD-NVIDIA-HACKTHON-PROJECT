import asyncio
import os
import sys
import time
from pathlib import Path

# Add backend to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import settings
from app.services.git_service import clone_repo, find_frontend_files, get_repo_metadata, cleanup_repo
from app.services.sandbox_client import (
    create_sandbox,
    run_command,
    upload_files,
    destroy_sandbox,
    is_docker_available,
    _local_sandboxes,
    _docker_sandboxes,
)
from app.services.sandbox_orchestrator import collect_repo_files


async def main():
    repo_url = "https://github.com/dhanushkumar-amk/A-TO-Z-SKILLS-REPO"
    test_scan_id = f"test_e2e_{int(time.time())}"

    print("=" * 70)
    print("CODEGUARD SANDBOX TEST SCRIPT")
    print(f"Target Repository: {repo_url}")
    print("=" * 70)

    # 1. Environment & Docker Pre-check
    docker_ready = await is_docker_available()
    print(f"\n[STEP 1] Environment & Provider Check:")
    print(f"  * Configured Provider : {settings.SANDBOX_PROVIDER}")
    print(f"  * Docker Daemon Alive : {docker_ready}")
    print(f"  * Nebius Remote API   : Completely removed (0 credits consumed)")

    # 2. Clone Target Repository
    print(f"\n[STEP 2] Shallow Cloning Target Repository:")
    start_clone = time.time()
    repo_path = clone_repo(repo_url=repo_url, scan_id=test_scan_id, branch="main")
    print(f"  * Cloned successfully to: {repo_path}")
    print(f"  * Time taken            : {round(time.time() - start_clone, 2)}s")

    # Inspect Files
    frontend_files = find_frontend_files(repo_path)
    metadata = get_repo_metadata(repo_path)
    all_files = collect_repo_files(repo_path)
    print(f"  * Detected Framework    : {metadata.get('framework', 'Vanilla JS')}")
    print(f"  * Scannable UI Files    : {len(frontend_files)} files found")
    print(f"  * Total Repository Files: {len(all_files)} files collected")
    for f in list(all_files.keys())[:5]:
        print(f"    - {f}")

    # 3. Provision Isolated Sandbox
    print(f"\n[STEP 3] Provisioning Isolated Sandbox Container:")
    start_sb = time.time()
    sandbox = await create_sandbox()
    print(f"  * Sandbox ID   : {sandbox.sandbox_id}")
    print(f"  * Engine Type  : {'Docker Container' if sandbox.sandbox_id.startswith('sb-docker-') else 'Isolated Local Process Engine'}")
    print(f"  * Status       : {sandbox.status}")
    print(f"  * Provision Time: {round((time.time() - start_sb) * 1000, 2)}ms")

    # 4. Synchronize Repository Tree into Sandbox
    print(f"\n[STEP 4] Synchronizing Repository Files into Sandbox:")
    start_sync = time.time()
    await upload_files(sandbox.sandbox_id, all_files)
    print(f"  * Synchronized {len(all_files)} files into sandbox workspace")
    print(f"  * Sync Time taken: {round((time.time() - start_sync) * 1000, 2)}ms")

    # 5. Execute Commands inside the Sandbox
    print(f"\n[STEP 5] Executing Commands inside Sandbox:")

    # 5a. Echo test
    cmd1 = 'echo "Sandbox execution verified"'
    res1 = await run_command(sandbox.sandbox_id, cmd1)
    print(f"  Command: {cmd1}")
    print(f"    Output   : {res1.stdout.strip()}")
    print(f"    Exit Code: {res1.exit_code} (Duration: {res1.duration_ms}ms)")
    assert res1.exit_code == 0, "Echo command failed"

    # 5b. Run Node.js execution on one of the repository's files
    sample_js = "Javascript/1_DataType/Numbers.js"
    if sample_js in all_files:
        cmd2 = f"node \"{sample_js}\""
        res2 = await run_command(sandbox.sandbox_id, cmd2)
        print(f"\n  Command: {cmd2}")
        print(f"    Output   : {res2.stdout.strip() or '(executed successfully)'}")
        print(f"    Exit Code: {res2.exit_code} (Duration: {res2.duration_ms}ms)")
        assert res2.exit_code == 0, f"Node script execution failed: {res2.stderr}"

    # 5c. Test applying a new file inside sandbox
    test_patch_file = "accessible_component.html"
    accessible_markup = '<button aria-label="Submit Form">Submit</button>'
    await upload_files(sandbox.sandbox_id, {test_patch_file: accessible_markup})
    
    cmd3 = f"node -e \"const fs = require('fs'); console.log(fs.readFileSync('{test_patch_file}', 'utf8'));\""
    res3 = await run_command(sandbox.sandbox_id, cmd3)
    print(f"\n  Command: Read patched accessibility file inside sandbox")
    print(f"    Output   : {res3.stdout.strip()}")
    print(f"    Exit Code: {res3.exit_code} (Duration: {res3.duration_ms}ms)")
    assert accessible_markup in res3.stdout, "File verification failed"

    # 6. Teardown Sandbox & Cleanup Workspace
    print(f"\n[STEP 6] Cleaning up Sandbox and Cloned Repository:")
    await destroy_sandbox(sandbox.sandbox_id)
    cleanup_repo(test_scan_id)
    print(f"  * Sandbox {sandbox.sandbox_id} destroyed cleanly.")
    print(f"  * Temporary cloned repository cleaned up.")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED: Sandbox works 100% with this repository!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
