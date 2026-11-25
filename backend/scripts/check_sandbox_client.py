"""Check CodeGuard's configured sandbox provider and guaranteed cleanup."""

import asyncio

from app.services.sandbox_client import run_command, sandbox_session, upload_files


async def main() -> None:
    async with sandbox_session() as sandbox:
        print(f"Sandbox: {sandbox.sandbox_id}")
        await upload_files(sandbox.sandbox_id, {"check.txt": "codeguard modal works\n"})
        result = await run_command(sandbox.sandbox_id, "cat check.txt", timeout=10)
        if result.exit_code != 0 or result.stdout.strip() != "codeguard modal works":
            raise RuntimeError(f"Sandbox check failed: {result.stderr}")
        print(result.stdout.strip())
        browser = await run_command(
            sandbox.sandbox_id,
            "node -e \"const {chromium}=require('playwright'); require('axe-core'); chromium.launch({headless:true}).then(b=>b.close())\"",
            timeout=20,
        )
        if browser.exit_code != 0:
            raise RuntimeError(f"Browser verification failed: {browser.stderr}")
        print("Playwright and axe-core ready")
    print("Sandbox terminated")


if __name__ == "__main__":
    asyncio.run(main())
