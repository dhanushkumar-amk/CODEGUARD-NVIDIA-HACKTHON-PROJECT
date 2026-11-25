"""Create a short-lived Modal sandbox, execute a command, then terminate it."""

import asyncio

import modal


async def main() -> None:
    app = await modal.App.lookup.aio("codeguard-sandboxes", create_if_missing=True)
    sandbox = await modal.Sandbox.create.aio(
        app=app,
        image=modal.Image.from_registry("python:3.13-slim"),
        timeout=60,
        cpu=0.5,
        memory=512,
    )
    try:
        process = await sandbox.exec.aio("python", "-c", "print('sandbox works')", timeout=10)
        output = await process.stdout.read.aio()
        print(output.strip())
        await process.wait.aio()
        if process.returncode != 0:
            raise RuntimeError(f"Sandbox command failed with exit code {process.returncode}")
    finally:
        await sandbox.terminate.aio()
        print("Sandbox terminated")


if __name__ == "__main__":
    asyncio.run(main())
