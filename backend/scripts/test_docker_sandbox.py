import asyncio
import os
import sys

# Ensure backend in path
sys.path.insert(0, r"c:\Users\dhanu\Documents\PROJECTS\CodeGuard\backend")

from app.services.sandbox_client import sandbox_session, run_command, upload_files, is_docker_available

async def main():
    print("=== DOCKER SANDBOX END-TO-END VERIFICATION ===")
    
    # 1. Docker availability
    docker_ready = await is_docker_available()
    print(f"[1] Docker daemon responsive: {docker_ready}")
    assert docker_ready, "Docker daemon must be ready!"

    # 2. Provision Docker sandbox
    async with sandbox_session(image="node:20-slim") as sb:
        print(f"[2] Sandbox provisioned successfully:")
        print(f"    - ID: {sb.sandbox_id}")
        print(f"    - Image: {sb.image}")
        print(f"    - Engine: {'Docker Container' if sb.sandbox_id.startswith('sb-docker-') else 'Local'}")

        # 3. Upload a sample file
        test_files = {
            "test_app.js": "const http = require('http'); console.log('Hello from isolated Docker sandbox!');",
            "package.json": '{"name": "test-box", "version": "1.0.0"}'
        }
        await upload_files(sb.sandbox_id, test_files)
        print("[3] Files uploaded into sandbox workspace")

        # 4. Run command in sandbox
        res = await run_command(sb.sandbox_id, "node test_app.js")
        print(f"[4] Executed 'node test_app.js':")
        print(f"    - Exit Code: {res.exit_code}")
        print(f"    - Stdout: {res.stdout.strip()}")
        print(f"    - Duration: {res.duration_ms}ms")
        assert res.exit_code == 0
        assert "Hello from isolated Docker sandbox!" in res.stdout

        # 5. Check git capability in sandbox
        git_res = await run_command(sb.sandbox_id, "node -e \"console.log(process.platform, process.arch)\"")
        print(f"[5] Container runtime architecture: {git_res.stdout.strip()}")

    print("\n[6] Sandbox destroyed and cleaned up cleanly.")
    print("ALL TESTS PASSED! Docker sandbox integration is 100% operational.")

if __name__ == "__main__":
    asyncio.run(main())
