import pytest
import uuid
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_idempotent_report_sync(client):
    """
    Test Tier 1: Even if an edge node retries a batch 3 times due to bad network,
    the server ingests the report exactly once.
    """
    m_id = str(uuid.uuid4())
    batch_payload = {
        "device_id": "phone-volunteer-unit-1",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": m_id,
                "entity_type": "REPORT",
                "action": "CREATE",
                "base_version": None,
                "payload": {
                    "client_assigned_uuid": m_id,
                    "reporter_name": "Anna",
                    "latitude": 37.77,
                    "longitude": -122.42,
                    "raw_text": "Flooding on lower level, 2 people need dry shelter."
                }
            }
        ]
    }

    # First push
    res1 = await client.post("/api/v1/sync/push", json=batch_payload)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["results"][0]["status"] == "APPLIED"

    # Second push (identical retry)
    res2 = await client.post("/api/v1/sync/push", json=batch_payload)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["results"][0]["status"] == "DUPLICATE_IGNORED"


@pytest.mark.asyncio
async def test_commutative_inventory_deltas(client):
    """
    Test Tier 2: Commutative delta merging ensures distributed volunteer updates
    never overwrite one another.
    """
    # 1. Create a shelter
    shelter_uuid = str(uuid.uuid4())
    shelter_payload = {
        "device_id": "test-device",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": shelter_uuid,
                "entity_type": "SHELTER",
                "action": "CREATE",
                "base_version": None,
                "payload": {
                    "client_assigned_uuid": shelter_uuid,
                    "name": "Delta Test Shelter",
                    "address": "123 Main St",
                    "latitude": 37.77,
                    "longitude": -122.42,
                    "total_capacity": 100,
                    "status": "OPEN"
                }
            }
        ]
    }
    s_res = await client.post("/api/v1/sync/push", json=shelter_payload)
    shelter_id = s_res.json()["results"][0]["entity_id"]

    # 2. Volunteer A applies delta +100
    delta_a = {
        "device_id": "device-a",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "INVENTORY",
                "action": "DELTA",
                "payload": {
                    "shelter_id": shelter_id,
                    "resource_type_code": "POTABLE_WATER",
                    "delta": 100.0
                }
            }
        ]
    }
    res_a = await client.post("/api/v1/sync/push", json=delta_a)
    assert res_a.json()["results"][0]["status"] == "APPLIED"

    # 3. Volunteer B applies delta -30
    delta_b = {
        "device_id": "device-b",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "INVENTORY",
                "action": "DELTA",
                "payload": {
                    "shelter_id": shelter_id,
                    "resource_type_code": "POTABLE_WATER",
                    "delta": -30.0
                }
            }
        ]
    }
    res_b = await client.post("/api/v1/sync/push", json=delta_b)
    assert res_b.json()["results"][0]["status"] == "APPLIED"

    # 4. Check pull delta
    pull_res = await client.get("/api/v1/sync/pull")
    inv_items = [i for i in pull_res.json()["inventory"] if i["shelter_id"] == shelter_id]
    assert len(inv_items) == 1
    assert inv_items[0]["quantity"] == 70.0


@pytest.mark.asyncio
async def test_occ_conflict_isolation(client):
    """
    Test Tier 3: If two volunteers concurrently modify shelter status from the same base version,
    the second update is quarantined as CONFLICT_ISOLATED without silent overwrite.
    """
    # 1. Create shelter
    s_uuid = str(uuid.uuid4())
    init_batch = {
        "device_id": "test-device",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": s_uuid,
                "entity_type": "SHELTER",
                "action": "CREATE",
                "payload": {
                    "client_assigned_uuid": s_uuid,
                    "name": "OCC Concurrency Shelter",
                    "address": "456 Market St",
                    "latitude": 37.78,
                    "longitude": -122.40,
                    "total_capacity": 80,
                    "status": "OPEN"
                }
            }
        ]
    }
    init_res = await client.post("/api/v1/sync/push", json=init_batch)
    shelter_id = init_res.json()["results"][0]["entity_id"]

    # 2. Volunteer 1 updates status from v1 -> v2
    v1_batch = {
        "device_id": "volunteer-1",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "SHELTER",
                "action": "UPDATE",
                "base_version": 1,
                "payload": {
                    "id": shelter_id,
                    "status": "FULL"
                }
            }
        ]
    }
    res_v1 = await client.post("/api/v1/sync/push", json=v1_batch)
    assert res_v1.json()["results"][0]["status"] == "APPLIED"
    assert res_v1.json()["results"][0]["resulting_version"] == 2

    # 3. Volunteer 2 (who went offline at v1) attempts to update status to EVACUATING with base_version=1
    v2_batch = {
        "device_id": "volunteer-2",
        "client_sent_at": datetime.now(timezone.utc).isoformat(),
        "batch": [
            {
                "mutation_id": str(uuid.uuid4()),
                "entity_type": "SHELTER",
                "action": "UPDATE",
                "base_version": 1,  # Stale version!
                "payload": {
                    "id": shelter_id,
                    "status": "EVACUATING"
                }
            }
        ]
    }
    res_v2 = await client.post("/api/v1/sync/push", json=v2_batch)
    assert res_v2.json()["results"][0]["status"] == "CONFLICT_ISOLATED"
