import httpx
import json

r = httpx.get("https://codeguard-backend-6pg4.onrender.com/api/report/scan_01ec0c1d")
data = r.json()
print("Status:", data.get("status"))
print("Summary:", json.dumps(data.get("summary", {}), indent=2))
print("Unified records count:", len(data.get("unified_records", [])))
print("Executive summary snippet:", (data.get("executive_summary") or "")[:200])
