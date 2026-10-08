"""
Full End-to-End Live Rehearsal Script:
Tests the LIVE deployed backend at https://codeguard-backend-6pg4.onrender.com
and WebSocket wss://codeguard-backend-6pg4.onrender.com
"""
import asyncio
import functools
import json
import os
import sys
import time
from pathlib import Path

print = functools.partial(print, flush=True)

try:
    import httpx
    import websockets
except ImportError:
    print("Installing httpx and websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "websockets"])
    import httpx
    import websockets

BACKEND_HTTP = os.environ.get("LIVE_API_URL", "https://codeguard-backend-6pg4.onrender.com")
BACKEND_WS = os.environ.get("LIVE_WS_URL", "wss://codeguard-backend-6pg4.onrender.com")
DEMO_REPO = "https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT"
UNAUTHORIZED_REPO = "https://github.com/octocat/Spoon-Knife"

async def test_failure_invalid_repo(client: httpx.AsyncClient):
    print("\n" + "="*70)
    print("TEST: Failure Path - Invalid Repo URL")
    print("="*70)
    try:
        resp = await client.post(
            f"{BACKEND_HTTP}/api/scan/start",
            json={"repo_url": "https://not-github.com/invalid/url", "branch": "main"},
            timeout=15.0,
        )
        print(f"Status Code: {resp.status_code}")
        print(f"Response: {resp.text}")
        if resp.status_code in (400, 422):
            print(">>> SUCCESS: Invalid repo URL rejected cleanly with 400/422.")
            return True
        else:
            print(f">>> FAILED: Unexpected status code: {resp.status_code}")
            return False
    except Exception as e:
        print(f">>> ERROR during invalid repo test: {e}")
        return False

async def run_live_scan_and_websocket():
    print("\n" + "="*70)
    print("TEST: Happy Path - Live Scan & Realtime WebSocket Stream")
    print(f"Target Repo: {DEMO_REPO}")
    print(f"Backend HTTP: {BACKEND_HTTP}")
    print(f"Backend WS: {BACKEND_WS}")
    print("="*70)

    stage_timings = {}
    scan_start_time = time.time()

    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Health check
        health_resp = await client.get(f"{BACKEND_HTTP}/health")
        print(f"[1] Backend Health Check: {health_resp.status_code} -> {health_resp.json()}")

        # 2. Start Scan
        print("[2] Initiating scan via POST /api/scan/start...")
        t0 = time.time()
        start_resp = await client.post(
            f"{BACKEND_HTTP}/api/scan/start",
            json={"repo_url": DEMO_REPO, "branch": "main"},
            timeout=60.0,
        )
        print(f"    Status: {start_resp.status_code}")
        start_data = start_resp.json()
        print(f"    Payload: {start_data}")

        if start_resp.status_code != 200:
            print(f">>> FAILED to initiate scan: {start_data}")
            return None

        scan_id = start_data["scan_id"]
        print(f"    Scan ID: {scan_id}")
        stage_timings["start_request_latency"] = time.time() - t0

        # 3. Connect to WebSocket
        ws_url = f"{BACKEND_WS}/ws/{scan_id}"
        print(f"\n[3] Connecting to live WebSocket: {ws_url}...")

        stages_seen = set()
        completed = False
        final_ws_message = None
        last_stage = None
        last_stage_time = time.time()

        try:
            async with websockets.connect(ws_url) as ws:
                print("    Connected to WebSocket! Streaming pipeline events...")
                while True:
                    try:
                        msg_raw = await asyncio.wait_for(ws.recv(), timeout=120)
                        msg = json.loads(msg_raw)
                        stage = msg.get("stage")
                        progress = msg.get("progress", 0)
                        text = msg.get("message", "")
                        data = msg.get("data") or {}

                        now = time.time()
                        if stage != last_stage:
                            if last_stage:
                                stage_timings[last_stage] = now - last_stage_time
                            last_stage = stage
                            last_stage_time = now

                        stages_seen.add(stage)
                        print(f"    [{progress:3d}%] Stage: {stage:<20} | {text}")
                        if "violations_found" in data:
                            print(f"          -> Violations: {data['violations_found']}, Cost: ${data.get('current_cost_usd', 0):.4f}")

                        if stage in ("complete", "completed"):
                            completed = True
                            final_ws_message = msg
                            if last_stage:
                                stage_timings[last_stage] = now - last_stage_time
                            break

                        if stage == "error":
                            print(f">>> ERROR reported by pipeline: {text}")
                            break

                    except asyncio.TimeoutError:
                        print(">>> WebSocket idle timeout waiting for next event (2m). Checking report API...")
                        break

        except Exception as ws_err:
            print(f">>> WebSocket connection warning: {ws_err}")

        total_scan_time = time.time() - scan_start_time
        print(f"\n>>> Total Scan Time (Click to Finish): {total_scan_time:.2f}s ({total_scan_time/60:.2f} mins)")
        print(f"Stages observed: {stages_seen}")

        # 4. Fetch Report from /api/report/{scan_id}
        print("\n[4] Fetching consolidated report from GET /api/report/{scan_id}...")
        report_resp = await client.get(f"{BACKEND_HTTP}/api/report/{scan_id}", timeout=30.0)
        print(f"    Report API status: {report_resp.status_code}")
        report_data = report_resp.json()

        # 5. Test Download HTML & Markdown endpoints
        print("\n[5] Testing Report Export Endpoints:")
        dl_resp = await client.get(f"{BACKEND_HTTP}/api/report/{scan_id}/download", timeout=30.0)
        print(f"    GET /download status: {dl_resp.status_code}, Content-Length: {len(dl_resp.content)} bytes")

        md_resp = await client.get(f"{BACKEND_HTTP}/api/report/{scan_id}/markdown", timeout=30.0)
        print(f"    GET /markdown status: {md_resp.status_code}, Length: {len(md_resp.text)} chars")

        # 6. Test Failure Case: Unauthorized PR
        print("\n[6] Testing PR Failure Path (Unauthorized / Foreign Repo)...")
        fail_pr_resp = await client.post(
            f"{BACKEND_HTTP}/api/report/{scan_id}/create-pr",
            json={"repo_url": UNAUTHORIZED_REPO},
            timeout=30.0,
        )
        print(f"    Status: {fail_pr_resp.status_code}")
        fail_pr_data = fail_pr_resp.json()
        print(f"    Payload: {fail_pr_data}")
        unauth_handled = fail_pr_data.get("status") == "failed"
        print(f"    Graceful rejection: {unauth_handled}")

        # 7. Test Real PR Creation on Demo Repo
        print("\n[7] Testing PR Creation on Demo Repo (POST /api/report/{scan_id}/create-pr)...")
        pr_resp = await client.post(
            f"{BACKEND_HTTP}/api/report/{scan_id}/create-pr",
            json={"repo_url": DEMO_REPO},
            timeout=30.0,
        )
        print(f"    PR status code: {pr_resp.status_code}")
        pr_data = pr_resp.json()
        print(f"    PR response payload: {pr_data}")

        return {
            "scan_id": scan_id,
            "total_scan_time": total_scan_time,
            "stage_timings": stage_timings,
            "stages_seen": list(stages_seen),
            "report": report_data,
            "html_download_ok": dl_resp.status_code == 200 and len(dl_resp.content) > 100,
            "markdown_ok": md_resp.status_code == 200 and len(md_resp.text) > 100,
            "unauth_handled": unauth_handled,
            "pr_result": pr_data,
        }

async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        invalid_ok = await test_failure_invalid_repo(client)

    results = await run_live_scan_and_websocket()
    if results:
        results["invalid_repo_tested"] = invalid_ok
        with open("rehearsal_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\n" + "="*70)
        print("REHEARSAL COMPLETED SUCCESSFULLY! Saved to rehearsal_results.json")
        print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
