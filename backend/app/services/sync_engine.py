from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.shelter import Shelter
from app.models.inventory import ShelterInventory, ResourceType
from app.models.report import EmergencyReport, AssistanceRequest
from app.models.sync import SyncAuditLog
from app.schemas.sync import (
    SyncPushRequest, SyncMutationResult, SyncPushResponse, SyncPullResponse
)
from app.services.conflict_resolver import ConflictResolver
from app.services.ml_classifier import classifier
from app.models.base import get_utc_now


class SyncEngine:
    """
    Orchestrates distributed sync push batches and pull delta streams.
    Enforces idempotency, commutativity, and OCC guarantees.
    """

    @staticmethod
    async def process_push_batch(
        db: AsyncSession,
        push_request: SyncPushRequest,
        user_id: Optional[str] = None
    ) -> SyncPushResponse:
        results: List[SyncMutationResult] = []
        now = get_utc_now()

        for item in push_request.batch:
            m_id = item.mutation_id
            e_type = item.entity_type.upper()
            action = item.action.upper()
            payload = item.payload
            client_ts = item.client_timestamp or push_request.client_sent_at

            try:
                # -------------------------------------------------------------
                # Tier 1: Monotonic Append-Only Reports
                # -------------------------------------------------------------
                if e_type == "REPORT" and action == "CREATE":
                    client_uuid = payload.get("client_assigned_uuid") or m_id
                    
                    # Idempotency check
                    stmt = select(EmergencyReport).where(EmergencyReport.client_assigned_uuid == client_uuid)
                    existing = (await db.execute(stmt)).scalar_one_or_none()

                    if existing:
                        results.append(SyncMutationResult(
                            mutation_id=m_id,
                            status="DUPLICATE_IGNORED",
                            entity_id=existing.id,
                            resulting_version=existing.version,
                            message="Report already ingested via previous sync packet."
                        ))
                        continue

                    # Automated NLP Triage
                    raw_text = payload.get("raw_text", "")
                    ml_result = classifier.predict(raw_text)
                    
                    cat = payload.get("category") or ml_result["category"]
                    urg = payload.get("urgency") or ml_result["urgency"]
                    confidence = ml_result["confidence"]
                    summary = f"Detected: {', '.join(ml_result['keywords'])}" if ml_result['keywords'] else None

                    new_report = EmergencyReport(
                        client_assigned_uuid=client_uuid,
                        reporter_name=payload.get("reporter_name"),
                        contact_info=payload.get("contact_info"),
                        latitude=float(payload.get("latitude", 0.0)),
                        longitude=float(payload.get("longitude", 0.0)),
                        address_hint=payload.get("address_hint"),
                        category=cat,
                        urgency=urg,
                        status="SUBMITTED",
                        raw_text=raw_text,
                        ai_summary=summary,
                        ai_confidence=confidence,
                        client_created_at=client_ts,
                        server_received_at=now,
                        version=1
                    )
                    db.add(new_report)
                    await db.flush()

                    audit = SyncAuditLog(
                        client_device_id=push_request.device_id,
                        user_id=user_id,
                        action_type="CREATE",
                        entity_name="REPORT",
                        entity_id=new_report.id,
                        base_version=None,
                        resulting_version=1,
                        payload=payload,
                        sync_status="APPLIED",
                        client_timestamp=client_ts
                    )
                    db.add(audit)
                    await db.commit()

                    results.append(SyncMutationResult(
                        mutation_id=m_id,
                        status="APPLIED",
                        entity_id=new_report.id,
                        resulting_version=1,
                        message="Report successfully ingested and triaged."
                    ))

                # -------------------------------------------------------------
                # Tier 2: Commutative Inventory Deltas
                # -------------------------------------------------------------
                elif e_type == "INVENTORY" and action == "DELTA":
                    shelter_id = payload.get("shelter_id")
                    res_code = payload.get("resource_type_code") or payload.get("resource_type_id")
                    delta_val = float(payload.get("delta", 0.0))

                    status, resulting_ver, err = await ConflictResolver.apply_inventory_delta(
                        db=db,
                        shelter_id=shelter_id,
                        resource_type_code=res_code,
                        delta=delta_val,
                        device_id=push_request.device_id,
                        client_timestamp=client_ts,
                        base_version=item.base_version,
                        user_id=user_id
                    )

                    results.append(SyncMutationResult(
                        mutation_id=m_id,
                        status=status,
                        entity_id=shelter_id,
                        resulting_version=resulting_ver,
                        message=err or "Inventory delta merged commutatively."
                    ))

                # -------------------------------------------------------------
                # Tier 3: OCC Structural Updates (Shelters)
                # -------------------------------------------------------------
                elif e_type == "SHELTER" and action == "UPDATE":
                    shelter_id = payload.get("id") or payload.get("shelter_id")
                    base_ver = item.base_version or payload.get("base_version", 1)

                    status, resulting_ver, err = await ConflictResolver.evaluate_shelter_update(
                        db=db,
                        shelter_id=shelter_id,
                        incoming_payload=payload,
                        base_version=base_ver,
                        device_id=push_request.device_id,
                        client_timestamp=client_ts,
                        user_id=user_id
                    )

                    results.append(SyncMutationResult(
                        mutation_id=m_id,
                        status=status,
                        entity_id=shelter_id,
                        resulting_version=resulting_ver,
                        message=err or "Shelter details updated."
                    ))

                elif e_type == "SHELTER" and action == "CREATE":
                    client_uuid = payload.get("client_assigned_uuid") or m_id
                    stmt = select(Shelter).where(Shelter.client_assigned_uuid == client_uuid)
                    existing_s = (await db.execute(stmt)).scalar_one_or_none()

                    if existing_s:
                        results.append(SyncMutationResult(
                            mutation_id=m_id,
                            status="DUPLICATE_IGNORED",
                            entity_id=existing_s.id,
                            resulting_version=existing_s.version,
                            message="Shelter already registered."
                        ))
                        continue

                    new_shelter = Shelter(
                        client_assigned_uuid=client_uuid,
                        name=payload.get("name"),
                        address=payload.get("address"),
                        latitude=float(payload.get("latitude")),
                        longitude=float(payload.get("longitude")),
                        total_capacity=int(payload.get("total_capacity", 50)),
                        current_occupancy=int(payload.get("current_occupancy", 0)),
                        status=payload.get("status", "OPEN"),
                        contact_phone=payload.get("contact_phone"),
                        version=1
                    )
                    db.add(new_shelter)
                    await db.flush()

                    audit = SyncAuditLog(
                        client_device_id=push_request.device_id,
                        user_id=user_id,
                        action_type="CREATE",
                        entity_name="SHELTER",
                        entity_id=new_shelter.id,
                        base_version=None,
                        resulting_version=1,
                        payload=payload,
                        sync_status="APPLIED",
                        client_timestamp=client_ts
                    )
                    db.add(audit)
                    await db.commit()

                    results.append(SyncMutationResult(
                        mutation_id=m_id,
                        status="APPLIED",
                        entity_id=new_shelter.id,
                        resulting_version=1,
                        message="Shelter created successfully."
                    ))

                # -------------------------------------------------------------
                # Assistance Requests
                # -------------------------------------------------------------
                elif e_type == "REQUEST" and action == "CREATE":
                    client_uuid = payload.get("client_assigned_uuid") or m_id
                    stmt = select(AssistanceRequest).where(AssistanceRequest.client_assigned_uuid == client_uuid)
                    existing_r = (await db.execute(stmt)).scalar_one_or_none()

                    if existing_r:
                        results.append(SyncMutationResult(
                            mutation_id=m_id,
                            status="DUPLICATE_IGNORED",
                            entity_id=existing_r.id,
                            resulting_version=existing_r.version,
                            message="Assistance request already enqueued."
                        ))
                        continue

                    new_req = AssistanceRequest(
                        client_assigned_uuid=client_uuid,
                        emergency_report_id=payload.get("emergency_report_id"),
                        shelter_id=payload.get("shelter_id"),
                        resource_type_id=payload.get("resource_type_id"),
                        requested_quantity=float(payload.get("requested_quantity", 1.0)),
                        fulfilled_quantity=0.0,
                        status="PENDING",
                        priority_score=int(payload.get("priority_score", 50)),
                        version=1
                    )
                    db.add(new_req)
                    await db.flush()

                    audit = SyncAuditLog(
                        client_device_id=push_request.device_id,
                        user_id=user_id,
                        action_type="CREATE",
                        entity_name="REQUEST",
                        entity_id=new_req.id,
                        base_version=None,
                        resulting_version=1,
                        payload=payload,
                        sync_status="APPLIED",
                        client_timestamp=client_ts
                    )
                    db.add(audit)
                    await db.commit()

                    results.append(SyncMutationResult(
                        mutation_id=m_id,
                        status="APPLIED",
                        entity_id=new_req.id,
                        resulting_version=1,
                        message="Assistance request registered."
                    ))

                else:
                    results.append(SyncMutationResult(
                        mutation_id=m_id,
                        status="ERROR",
                        message=f"Unsupported entity/action combination: {e_type} / {action}"
                    ))

            except Exception as ex:
                await db.rollback()
                results.append(SyncMutationResult(
                    mutation_id=m_id,
                    status="ERROR",
                    message=f"Internal exception processing mutation: {str(ex)}"
                ))

        return SyncPushResponse(
            server_received_at=now,
            processed_count=len(results),
            results=results
        )

    @staticmethod
    async def get_pull_delta(
        db: AsyncSession,
        since_timestamp: Optional[datetime] = None
    ) -> SyncPullResponse:
        now = get_utc_now()

        # Query shelters
        s_query = select(Shelter)
        if since_timestamp:
            s_query = s_query.where(Shelter.updated_at >= since_timestamp)
        shelters = (await db.execute(s_query)).scalars().all()

        # Query resource types
        rt_query = select(ResourceType)
        resource_types = (await db.execute(rt_query)).scalars().all()

        # Query inventory
        i_query = select(ShelterInventory)
        if since_timestamp:
            i_query = i_query.where(ShelterInventory.updated_at >= since_timestamp)
        inventories = (await db.execute(i_query)).scalars().all()

        # Query reports
        r_query = select(EmergencyReport)
        if since_timestamp:
            r_query = r_query.where(EmergencyReport.updated_at >= since_timestamp)
        reports = (await db.execute(r_query)).scalars().all()

        return SyncPullResponse(
            server_timestamp=now,
            shelters=[
                {
                    "id": s.id,
                    "client_assigned_uuid": s.client_assigned_uuid,
                    "name": s.name,
                    "address": s.address,
                    "latitude": s.latitude,
                    "longitude": s.longitude,
                    "total_capacity": s.total_capacity,
                    "current_occupancy": s.current_occupancy,
                    "status": s.status,
                    "contact_phone": s.contact_phone,
                    "version": s.version,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None
                }
                for s in shelters
            ],
            inventory=[
                {
                    "id": inv.id,
                    "shelter_id": inv.shelter_id,
                    "resource_type_id": inv.resource_type_id,
                    "quantity": inv.quantity,
                    "min_threshold": inv.min_threshold,
                    "version": inv.version,
                    "updated_at": inv.updated_at.isoformat() if inv.updated_at else None
                }
                for inv in inventories
            ],
            reports=[
                {
                    "id": rep.id,
                    "client_assigned_uuid": rep.client_assigned_uuid,
                    "reporter_name": rep.reporter_name,
                    "latitude": rep.latitude,
                    "longitude": rep.longitude,
                    "category": rep.category,
                    "urgency": rep.urgency,
                    "status": rep.status,
                    "raw_text": rep.raw_text,
                    "ai_summary": rep.ai_summary,
                    "ai_confidence": rep.ai_confidence,
                    "version": rep.version,
                    "updated_at": rep.updated_at.isoformat() if rep.updated_at else None
                }
                for rep in reports
            ],
            resource_types=[
                {
                    "id": rt.id,
                    "code": rt.code,
                    "name": rt.name,
                    "category": rt.category,
                    "unit": rt.unit,
                    "is_critical": rt.is_critical
                }
                for rt in resource_types
            ]
        )
