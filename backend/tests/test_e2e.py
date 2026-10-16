import io
import pytest


DETERMINISTIC_SALES_CSV = """product,category,revenue,units_sold,region
Laptop,Electronics,5000,10,North
Smartphone,Electronics,3000,15,North
Headphones,Electronics,1000,20,South
Desk Chair,Furniture,2000,8,South
Standing Desk,Furniture,4000,5,East
Coffee Maker,Appliances,800,12,East
Toaster,Appliances,200,10,West
"""


def test_full_end_to_end_analysis_workflow(client):
    """
    Complete end-to-end user workflow:
    1. Register user
    2. Upload sales dataset
    3. Verify data profiling (row counts, types, summary metrics)
    4. Ask analytical question: "Which products generated the highest revenue?"
    5. Verify real computed result (Laptop is #1 with 5000 revenue)
    6. Verify visualization recommendation (Bar chart)
    7. Generate and download CSV report
    8. Check saved analysis history
    """
    # 1. Register user
    reg = client.post("/api/v1/auth/register", json={
        "email": "lead_analyst@company.com",
        "password": "StrongSecretPassword123!"
    })
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload CSV
    upload_res = client.post(
        "/api/v1/datasets/upload",
        files={"file": ("sales_q3.csv", io.BytesIO(DETERMINISTIC_SALES_CSV.encode("utf-8")), "text/csv")},
        headers=headers
    )
    assert upload_res.status_code == 201
    dataset = upload_res.json()
    dataset_id = dataset["id"]
    assert dataset["row_count"] == 7
    assert dataset["column_count"] == 5

    # 3. Verify profiling
    profile_res = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
    assert profile_res.status_code == 200
    profile = profile_res.json()
    assert profile["row_count"] == 7
    rev_profile = next(c for c in profile["columns"] if c["name"] == "revenue")
    assert rev_profile["max"] == 5000.0
    assert rev_profile["min"] == 200.0

    # 4. Ask analytical question
    query_payload = {
        "dataset_id": dataset_id,
        "question": "Which products generated the highest revenue?"
    }
    analysis_res = client.post("/api/v1/analyses", json=query_payload, headers=headers)
    assert analysis_res.status_code == 201
    analysis_data = analysis_res.json()
    analysis_id = analysis_data["id"]

    assert analysis_data["status"] == "completed"
    assert analysis_data["result"] is not None
    rows = analysis_data["result"]["rows"]
    assert len(rows) > 0

    # 5. Verify real computed results (NOT fabricated!)
    # Top product should be Laptop with revenue 5000
    top_row = rows[0]
    assert top_row["product"] == "Laptop"
    assert top_row.get("revenue_sum") == 5000 or top_row.get("revenue") == 5000 or top_row.get("revenue_max") == 5000

    # Verify chart suggestion
    assert analysis_data["result"]["chart_type"] in ["bar", "pie", "line"]
    assert "Laptop" in analysis_data["explanation"]

    # 6. Generate Report
    report_res = client.post("/api/v1/reports", json={"analysis_id": analysis_id, "format": "csv"}, headers=headers)
    assert report_res.status_code == 201
    report = report_res.json()
    report_id = report["id"]

    # 7. Download Report
    download_res = client.get(f"/api/v1/reports/{report_id}/download", headers=headers)
    assert download_res.status_code == 200
    assert "text/csv" in download_res.headers.get("content-type", "")
    assert "Laptop" in download_res.text

    # 8. Verify Analyses History
    history_res = client.get(f"/api/v1/analyses?dataset_id={dataset_id}", headers=headers)
    assert history_res.status_code == 200
    history = history_res.json()
    assert len(history) >= 1
    assert history[0]["id"] == analysis_id
