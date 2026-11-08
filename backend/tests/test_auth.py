import pytest


@pytest.mark.asyncio
async def test_register_and_login_flow(client):
    # Register
    reg_payload = {
        "email": "testvolunteer@relay.org",
        "password": "securepassword123",
        "full_name": "Test Volunteer",
        "role": "VOLUNTEER",
        "phone": "+1-555-019-9999"
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "testvolunteer@relay.org"
    assert data["role"] == "VOLUNTEER"

    # Login
    login_payload = {
        "email": "testvolunteer@relay.org",
        "password": "securepassword123"
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Profile check
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "testvolunteer@relay.org"
