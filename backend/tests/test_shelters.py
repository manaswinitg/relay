import pytest


@pytest.mark.asyncio
async def test_shelter_creation_and_spatial_discovery(client):
    # 1. Register coordinator user
    reg_payload = {
        "email": "coordinator@test.org",
        "password": "strongpassword123",
        "full_name": "Test Coordinator",
        "role": "COORDINATOR",
        "phone": "+1-555-0100"
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201

    # Login to get valid token
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "coordinator@test.org",
        "password": "strongpassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Shelter near San Francisco (37.765, -122.420)
    s_payload = {
        "name": "Mission Relief Hub",
        "address": "16th & Mission St",
        "latitude": 37.765,
        "longitude": -122.420,
        "total_capacity": 120,
        "current_occupancy": 40,
        "status": "OPEN",
        "contact_phone": "+1-415-555-0199"
    }
    create_res = await client.post("/api/v1/shelters", json=s_payload, headers=headers)
    assert create_res.status_code == 201
    shelter_data = create_res.json()
    assert shelter_data["name"] == "Mission Relief Hub"
    assert shelter_data["version"] == 1

    # 3. Spatial discovery within 5 km
    nearby_res = await client.get("/api/v1/shelters/nearby?latitude=37.770&longitude=-122.425&radius_km=5.0")
    assert nearby_res.status_code == 200
    nearby_list = nearby_res.json()
    assert len(nearby_list) >= 1
    assert "distance_km" in nearby_list[0]
    assert nearby_list[0]["distance_km"] < 5.0
