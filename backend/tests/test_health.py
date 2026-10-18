def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert data["offline_engine_ready"] is True


def test_root_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_root_endpoint(client):
    res = client.get("/")
    assert res.status_code == 200
    data = res.json()
    assert "QueryPilot" in data["name"]
    assert data["docs"] == "/api/v1/docs"
    assert data["health"] == "/api/v1/health"


def test_docs_redirect(client):
    res = client.get("/docs", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == "/api/v1/docs"


def test_docs_canonical_endpoint(client):
    res = client.get("/api/v1/docs")
    assert res.status_code == 200
    assert "Swagger UI" in res.text or "swagger-ui" in res.text


def test_api_v1_root_redirect(client):
    res = client.get("/api/v1", follow_redirects=False)
    assert res.status_code in (302, 307)
    assert res.headers["location"] == "/api/v1/docs"

