from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.sync import ConflictRecord, SyncAuditLog
from app.models.shelter import Shelter
from app.models.user import User
from app.schemas.sync import (
    SyncPushRequest, SyncPushResponse, SyncPullResponse,
    ConflictRecordResponse, ConflictResolveRequest
)
from app.services.sync_engine import SyncEngine
from app.api.v1.endpoints.auth import get_current_user, require_roles
from app.models.base import get_utc_now

router = APIRouter()


@router.post("/push", response_model=SyncPushResponse)
async def sync_push(
    push_request: SyncPushRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Primary synchronization gateway for field nodes re-establishing connectivity.
    Processes a batch of offline mutations idempotently.
    """
    response = await SyncEngine.process_push_batch(
        db=db,
        push_request=push_request,
        user_id=None
    )
    return response


@router.get("/pull", response_model=SyncPullResponse)
async def sync_pull(
    since: Optional[datetime] = Query(None, description="ISO timestamp of last successful sync checkpoint"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns all entities updated since client's last sync checkpoint.
    """
    return await SyncEngine.get_pull_delta(db=db, since_timestamp=since)


@router.get("/conflicts", response_model=List[ConflictRecordResponse])
async def list_conflicts(
    resolution_status: Optional[str] = Query("PENDING_REVIEW"),
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ConflictRecord)
    if resolution_status:
        stmt = stmt.where(ConflictRecord.resolution_status == resolution_status.upper())
    stmt = stmt.order_by(ConflictRecord.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str,
    resolve_in: ConflictResolveRequest,
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Manual human-in-the-loop conflict adjudication by an authorized disaster coordinator.
    """
    stmt = select(ConflictRecord).where(ConflictRecord.id == conflict_id)
    conflict = (await db.execute(stmt)).scalar_one_or_none()
    if not conflict:
        raise HTTPException(status_code=404, detail="Conflict record not found.")

    if conflict.resolution_status != "PENDING_REVIEW":
        raise HTTPException(status_code=400, detail="Conflict has already been resolved.")

    resolution = resolve_in.resolution.upper()
    now = get_utc_now()

    if conflict.entity_type == "SHELTER":
        s_stmt = select(Shelter).where(Shelter.id == conflict.entity_id)
        shelter = (await db.execute(s_stmt)).scalar_one_or_none()

        if shelter:
            if resolution == "ACCEPT_CLIENT":
                # Apply client values
                for k, v in conflict.client_payload.items():
                    if hasattr(shelter, k) and k not in ["id", "version", "created_at"]:
                        setattr(shelter, k, v)
                shelter.version += 1
                shelter.updated_at = now
            elif resolution == "MANUAL_MERGE" and resolve_in.manual_payload:
                for k, v in resolve_in.manual_payload.items():
                    if hasattr(shelter, k) and k not in ["id", "version", "created_at"]:
                        setattr(shelter, k, v)
                shelter.version += 1
                shelter.updated_at = now
            # If ACCEPT_SERVER, we keep existing server state without modifications

    conflict.resolution_status = resolution
    conflict.resolved_by_user_id = current_user.id
    conflict.resolution_notes = resolve_in.resolution_notes
    conflict.resolved_at = now

    await db.commit()
    return {
        "status": "RESOLVED",
        "conflict_id": conflict_id,
        "resolution": resolution,
        "resolved_at": now.isoformat()
    }


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SyncAuditLog).order_by(SyncAuditLog.server_timestamp.desc()).limit(limit)
    logs = (await db.execute(stmt)).scalars().all()
    return logs
