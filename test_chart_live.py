"""
Live end-to-end test: verifies chart data mapping for the revenue-by-product query.
"""
import urllib.request
import urllib.error
import json
import sys
import os

BASE = "http://127.0.0.1:8000/api/v1"


def api_json(method, path, data=None, token=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def upload_csv(token, csv_content, filename="test_sales.csv"):
    boundary = "testboundary1234567890"
    body_parts = []
    body_parts.append(f"--{boundary}\r\n".encode())
    body_parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body_parts.append(b"Content-Type: text/csv\r\n\r\n")
    body_parts.append(csv_content.encode())
    body_parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    req = urllib.request.Request(
        BASE + "/datasets/upload",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req, timeout=10)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# --- Test ---
EMAIL = "charttest2025@test.com"
PASSWORD = "Test1234!"

print("=== QueryPilot Chart Data Live API Test ===\n")

# Register (ignore if already exists)
status, resp = api_json("POST", "/auth/register", {"email": EMAIL, "password": PASSWORD})
print(f"Register: {status}")

# Login
status, resp = api_json("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})
print(f"Login: {status}")
assert status == 200, f"Login failed: {resp}"
token = resp["access_token"]
print(f"Token acquired.\n")

# Upload 4-row CSV (aggregated) matching the user's expected values
csv_data = """product,quantity,unit_price,revenue
Laptop,17,1200,20400
Phone,30,610,18300
Desk,10,600,6000
Chair,27,190,5130
"""

status, upload = upload_csv(token, csv_data)
print(f"Upload: {status}")
if status not in (200, 201):
    print("Upload error:", upload)
    sys.exit(1)
dataset_id = upload["id"]
print(f"Dataset ID: {dataset_id}, rows={upload.get('row_count')}\n")

# Run analysis
QUESTION = "Which product generated the highest total revenue?"
status, analysis = api_json("POST", "/analyses", {
    "dataset_id": dataset_id,
    "question": QUESTION
}, token=token)
print(f"Analysis status: {status}")
if status not in (200, 201):
    print("Analysis error:", analysis)
    sys.exit(1)

result = analysis.get("result", {})
columns = result.get("columns", [])
rows = result.get("rows", [])
chart_config = result.get("chart_config", {})
chart_type = result.get("chart_type")

print(f"\nColumns: {columns}")
print(f"chart_type: {chart_type}")
print(f"chart_config: {chart_config}")
print(f"\nResult rows:")
for row in rows:
    print(f"  {row}")

# Verify chart mapping
x_axis = chart_config.get("x_axis") if chart_config else None
y_axis = chart_config.get("y_axis") if chart_config else None
print(f"\n--- Chart Axis Mapping ---")
print(f"x_axis key: '{x_axis}'")
print(f"y_axis key: '{y_axis}'")
print(f"\nChart data (as Recharts will see it):")

EXPECTED = {"Laptop": 20400, "Phone": 18300, "Desk": 6000, "Chair": 5130}
all_ok = True
for row in rows:
    x_val = row.get(x_axis)
    y_val = row.get(y_axis)
    expected_val = EXPECTED.get(x_val)
    ok = (y_val == expected_val)
    marker = "[OK]" if ok else "[MISMATCH]"
    print(f"  {x_val}: {y_val}  (expected {expected_val}) {marker}")
    if not ok:
        all_ok = False

print()
if all_ok:
    print("[OK] All chart data values are CORRECT")
else:
    print("[FAIL] Chart data contains incorrect values!")
    sys.exit(1)

print(f"\nExplanation: {analysis.get('explanation', '')}")
print("\n=== Test PASSED ===")
