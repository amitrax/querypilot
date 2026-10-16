import io
import pytest


SAMPLE_CSV = """product,category,revenue,units_sold,region
Laptop,Electronics,1200.50,5,North
Smartphone,Electronics,800.00,10,North
Desk Chair,Furniture,250.00,12,South
Office Desk,Furniture,450.00,4,South
Coffee Maker,Appliances,90.00,15,East
Blender,Appliances,60.00,8,East
"""

EMPTY_CSV = ""


def test_csv_upload_and_profiling(client, auth_headers):
    # 1. Upload valid CSV
    files = {"file": ("sales_data.csv", io.BytesIO(SAMPLE_CSV.encode("utf-8")), "text/csv")}
    res = client.post("/api/v1/datasets/upload", files=files, headers=auth_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "sales_data"
    assert data["row_count"] == 6
    assert data["column_count"] == 5
    dataset_id = data["id"]

    # 2. Preview dataset
    preview_res = client.get(f"/api/v1/datasets/{dataset_id}/preview?page=1&page_size=3", headers=auth_headers)
    assert preview_res.status_code == 200
    preview_data = preview_res.json()
    assert preview_data["total_rows"] == 6
    assert len(preview_data["rows"]) == 3
    assert "product" in preview_data["columns"]
    assert "revenue" in preview_data["columns"]

    # 3. Profile metrics
    profile_res = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=auth_headers)
    assert profile_res.status_code == 200
    profile_data = profile_res.json()
    assert profile_data["row_count"] == 6
    assert profile_data["duplicate_rows"] == 0

    col_names = [c["name"] for c in profile_data["columns"]]
    assert "product" in col_names
    assert "revenue" in col_names

    # Check numeric stats on revenue
    rev_col = next(c for c in profile_data["columns"] if c["name"] == "revenue")
    assert rev_col["inferred_type"] in ["float", "integer"]
    assert rev_col["min"] == 60.0
    assert rev_col["max"] == 1200.50

    # 4. List datasets
    list_res = client.get("/api/v1/datasets", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(d["id"] == dataset_id for d in list_res.json())

    # 5. Delete dataset
    del_res = client.delete(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
    assert del_res.status_code == 200

    # 6. Verify deleted
    get_res = client.get(f"/api/v1/datasets/{dataset_id}", headers=auth_headers)
    assert get_res.status_code == 404


def test_invalid_csv_uploads(client, auth_headers):
    # Non-CSV extension rejected
    files = {"file": ("data.txt", io.BytesIO(b"hello world"), "text/plain")}
    res = client.post("/api/v1/datasets/upload", files=files, headers=auth_headers)
    assert res.status_code == 400

    # Empty file rejected
    files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
    res = client.post("/api/v1/datasets/upload", files=files, headers=auth_headers)
    assert res.status_code == 400


def test_dataset_ownership_authorization(client, auth_headers):
    # User 1 uploads dataset
    files = {"file": ("user1_sales.csv", io.BytesIO(SAMPLE_CSV.encode("utf-8")), "text/csv")}
    res = client.post("/api/v1/datasets/upload", files=files, headers=auth_headers)
    assert res.status_code == 201
    dataset_id = res.json()["id"]

    # Register User 2
    u2_res = client.post("/api/v1/auth/register", json={"email": "user2@querypilot.dev", "password": "User2Pass123!"})
    assert u2_res.status_code == 201
    u2_token = u2_res.json()["access_token"]
    u2_headers = {"Authorization": f"Bearer {u2_token}"}

    # User 2 attempts to get User 1's dataset -> Forbidden (403)
    forbidden_get = client.get(f"/api/v1/datasets/{dataset_id}", headers=u2_headers)
    assert forbidden_get.status_code == 403

    # User 2 attempts to delete User 1's dataset -> Forbidden (403)
    forbidden_del = client.delete(f"/api/v1/datasets/{dataset_id}", headers=u2_headers)
    assert forbidden_del.status_code == 403
