import pytest
from app.core.security import verify_password, get_password_hash


def test_password_hashing():
    raw_pwd = "SuperSecretPassword123!"
    hashed = get_password_hash(raw_pwd)
    assert hashed != raw_pwd
    assert verify_password(raw_pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_user_registration_and_login(client):
    email = "newuser@querypilot.dev"
    password = "SecurePassword123!"

    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email

    # 2. Duplicate registration rejected
    dup_res = client.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert dup_res.status_code == 400

    # 3. Login with correct credentials
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    login_data = login_res.json()
    token = login_data["access_token"]
    assert token

    # 4. Login with invalid password rejected
    bad_login = client.post("/api/v1/auth/login", json={"email": email, "password": "WrongPassword"})
    assert bad_login.status_code == 401

    # 5. Get current user profile
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 6. Unauthorized access without token
    unauth_res = client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401
