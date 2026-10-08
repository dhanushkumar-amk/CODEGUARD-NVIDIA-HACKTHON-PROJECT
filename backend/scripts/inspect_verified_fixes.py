import httpx
import json

r = httpx.get("https://codeguard-backend-6pg4.onrender.com/api/report/scan_01ec0c1d")
data = r.json()
unified = data.get("unified_records", [])
verified = [u for u in unified if u.get("final_status") == "fixed_and_verified"]

print(f"Total verified fixes: {len(verified)}")
for idx, item in enumerate(verified, 1):
    v = item.get("violation") or {}
    f = item.get("fix") or {}
    print(f"\n[Verified Fix #{idx}]")
    print(f"  Violation ID: {v.get('id')}")
    print(f"  Violation File: {v.get('file')}")
    print(f"  Fix ID: {f.get('fix_id')}")
    print(f"  Fix File: {f.get('file')}")
    print(f"  Diff:\n{f.get('diff')}")
