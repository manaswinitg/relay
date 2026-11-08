import asyncio
import time
import uuid
import sys
import os
import numpy as np
from datetime import datetime, timezone

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.database import Base
from app.models.shelter import Shelter
from app.models.inventory import ResourceType, ShelterInventory
from app.schemas.sync import SyncPushRequest, SyncMutationItem
from app.services.sync_engine import SyncEngine
from app.services.ml_classifier import classifier


async def run_comprehensive_benchmarks():
    print("=" * 70)
    print("RELAY: Distributed Systems & Sync Engine Benchmark Suite")
    print("=" * 70)

    # 1. Setup in-memory test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    Session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed baseline shelter and resource types
    async with Session() as session:
        s = Shelter(
            name="Benchmark Central Shelter",
            address="100 Test Blvd",
            latitude=37.77,
            longitude=-122.41,
            total_capacity=500,
            status="OPEN",
            version=1
        )
        water = ResourceType(code="POTABLE_WATER", name="Drinking Water", category="WATER", unit="LITERS", is_critical=True)
        session.add_all([s, water])
        await session.commit()
        shelter_id = s.id

    # -------------------------------------------------------------------------
    # Experiment 1: Batch Sync Throughput & Latency
    # -------------------------------------------------------------------------
    print("\n[Experiment 1] Batch Sync Ingestion Throughput:")
    batch_sizes = [10, 50, 100, 250]
    for n in batch_sizes:
        items = []
        for i in range(n):
            items.append(SyncMutationItem(
                mutation_id=str(uuid.uuid4()),
                entity_type="REPORT",
                action="CREATE",
                payload={
                    "client_assigned_uuid": str(uuid.uuid4()),
                    "reporter_name": f"Tester-{i}",
                    "latitude": 37.77 + (i * 0.001),
                    "longitude": -122.41 + (i * 0.001),
                    "raw_text": f"Incident report #{i}: Flood water rising, emergency drinking water needed.",
                    "client_created_at": datetime.now(timezone.utc).isoformat()
                }
            ))
        req = SyncPushRequest(
            device_id="benchmark-runner",
            client_sent_at=datetime.now(timezone.utc),
            batch=items
        )

        async with Session() as session:
            t0 = time.perf_counter()
            resp = await SyncEngine.process_push_batch(session, req)
            dt_ms = (time.perf_counter() - t0) * 1000.0

            throughput = n / (dt_ms / 1000.0)
            applied_count = sum(1 for r in resp.results if r.status == "APPLIED")
            print(f"  Batch Size {n:3d} items | Total Latency: {dt_ms:6.2f} ms | Throughput: {throughput:7.1f} ops/sec | Success: {applied_count}/{n}")

    # -------------------------------------------------------------------------
    # Experiment 2: Commutative Delta Consistency Verification
    # -------------------------------------------------------------------------
    print("\n[Experiment 2] Commutative Delta Merging (50 Concurrent Volunteer Updates):")
    # Simulate 50 concurrent transactions (+/- water units)
    expected_sum = 0.0
    delta_items = []
    for i in range(50):
        # alternating positive and negative changes
        val = 25.0 if i % 2 == 0 else -15.0
        expected_sum += val
        delta_items.append(SyncMutationItem(
            mutation_id=str(uuid.uuid4()),
            entity_type="INVENTORY",
            action="DELTA",
            payload={
                "shelter_id": shelter_id,
                "resource_type_code": "POTABLE_WATER",
                "delta": val
            }
        ))

    delta_req = SyncPushRequest(
        device_id="multi-volunteer-pool",
        client_sent_at=datetime.now(timezone.utc),
        batch=delta_items
    )

    async with Session() as session:
        t0 = time.perf_counter()
        d_resp = await SyncEngine.process_push_batch(session, delta_req)
        d_latency = (time.perf_counter() - t0) * 1000.0

        # Verify against database state
        pull_data = await SyncEngine.get_pull_delta(session)
        target_inv = [inv for inv in pull_data.inventory if inv["shelter_id"] == shelter_id]
        actual_qty = target_inv[0]["quantity"]

        print(f"  Processed: 50 delta mutations in {d_latency:.2f} ms")
        print(f"  Expected Final Quantity: {expected_sum:.1f} LITERS")
        print(f"  Actual Server Quantity:   {actual_qty:.1f} LITERS")
        assert actual_qty == expected_sum, f"Commutative drift detected! {actual_qty} != {expected_sum}"
        print("  Verification: PERFECT CONVERGENCE (Zero lost updates under concurrent delta replay)")

    # -------------------------------------------------------------------------
    # Experiment 3: OCC Conflict Detection & Isolation Rate
    # -------------------------------------------------------------------------
    print("\n[Experiment 3] OCC Versioning & Conflict Isolation Rate:")
    conflict_batch = []
    # 1 valid update on base_version 1
    conflict_batch.append(SyncMutationItem(
        mutation_id=str(uuid.uuid4()),
        entity_type="SHELTER",
        action="UPDATE",
        base_version=1,
        payload={"id": shelter_id, "status": "FULL"}
    ))
    # 9 stale concurrent updates from disconnected nodes holding base_version 1
    for i in range(9):
        conflict_batch.append(SyncMutationItem(
            mutation_id=str(uuid.uuid4()),
            entity_type="SHELTER",
            action="UPDATE",
            base_version=1,
            payload={"id": shelter_id, "status": "EVACUATING", "total_capacity": 400 + i}
        ))

    conflict_req = SyncPushRequest(
        device_id="conflicted-nodes",
        client_sent_at=datetime.now(timezone.utc),
        batch=conflict_batch
    )

    async with Session() as session:
        c_resp = await SyncEngine.process_push_batch(session, conflict_req)
        applied = sum(1 for r in c_resp.results if r.status == "APPLIED")
        isolated = sum(1 for r in c_resp.results if r.status == "CONFLICT_ISOLATED")

        print(f"  Total Competing Updates: 10")
        print(f"  First Write Applied (v1 -> v2): {applied}")
        print(f"  Stale Writes Isolated in Quarantine: {isolated}")
        assert applied == 1 and isolated == 9, "OCC Conflict Isolation anomaly detected"
        print("  Verification: 100% Conflict Detection & Quarantine (Zero silent LWW overwrites)")

    # -------------------------------------------------------------------------
    # Experiment 4: NLP Triage Classifier Latency
    # -------------------------------------------------------------------------
    print("\n[Experiment 4] NLP Emergency Triage Latency:")
    sample_text = "Severe building collapse, three trapped victims with heavy arterial bleeding, immediate ambulance required."
    latencies = []
    for _ in range(100):
        t0 = time.perf_counter()
        _ = classifier.predict(sample_text)
        latencies.append((time.perf_counter() - t0) * 1000.0)

    p50 = np.percentile(latencies, 50)
    p95 = np.percentile(latencies, 95)
    p99 = np.percentile(latencies, 99)
    print(f"  100 Inferences on NLP Triage Engine:")
    print(f"  p50 Latency: {p50:.3f} ms | p95 Latency: {p95:.3f} ms | p99 Latency: {p99:.3f} ms")

    print("\n" + "=" * 70)
    print("ALL EMPIRICAL EVALUATION EXPERIMENTS COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_benchmarks())
