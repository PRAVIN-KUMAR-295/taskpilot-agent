import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.auth.security import hash_password, verify_password, create_access_token, decode_access_token

client = TestClient(app)


def test_password_hashing():
    raw = "SecureSecretPassword123!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_generation_and_decoding():
    token = create_access_token(user_id=42, email="architect@taskpilot.ai")
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "42"
    assert payload["email"] == "architect@taskpilot.ai"


def test_register_and_login_flow():
    import uuid
    uid = uuid.uuid4().hex[:6]
    email = f"new_engineer_{uid}@taskpilot.ai"
    reg_res = client.post("/api/auth/register", json={
        "name": "Cloud Engineer",
        "email": email,
        "password": "mypassword123"
    })

    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert reg_data["success"] is True
    assert "token" in reg_data
    assert reg_data["user"]["email"] == email

    # Re-registration with same email should fail
    dup_res = client.post("/api/auth/register", json={
        "name": "Cloud Engineer 2",
        "email": email,
        "password": "mypassword123"
    })
    assert dup_res.status_code == 400

    # Login with correct credentials
    login_res = client.post("/api/auth/login", json={
        "email": email,
        "password": "mypassword123"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["success"] is True
    assert "token" in login_data

    # Login with wrong password
    bad_login = client.post("/api/auth/login", json={
        "email": email,
        "password": "incorrect_password"
    })
    assert bad_login.status_code == 401
