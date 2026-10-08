import httpx
import json

scan_id = "scan_01ec0c1d"
api_base = "https://codeguard-backend-6pg4.onrender.com"

# 1. Test unauthorized repo failure
print("Testing unauthorized repo PR creation...")
r_unauth = httpx.post(
    f"{api_base}/api/report/{scan_id}/create-pr",
    json={"repo_url": "https://github.com/octocat/Spoon-Knife"},
    timeout=30.0,
)
print("Unauthorized Status:", r_unauth.status_code)
print("Unauthorized Response:", r_unauth.json())

# 2. Test demo repo PR creation
print("\nTesting demo repo PR creation...")
r_demo = httpx.post(
    f"{api_base}/api/report/{scan_id}/create-pr",
    json={"repo_url": "https://github.com/dhanushkumar-amk/CODEGUARD---NVIDIA-HACKTHON-PROJECT"},
    timeout=60.0,
)
print("Demo PR Status:", r_demo.status_code)
print("Demo PR Response:", r_demo.json())
