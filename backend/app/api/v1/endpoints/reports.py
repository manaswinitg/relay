from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.report import EmergencyReport, AssistanceRequest
from app.models.user import User
from app.schemas.report import (
    EmergencyReportCreate, EmergencyReportUpdate, EmergencyReportResponse,
    AssistanceRequestCreate, AssistanceRequestResponse
)
from app.services.ml_classifier import classifier
from app.api.v1.endpoints.auth import get_current_user, require_roles
from app.models.base import get_utc_now, generate_uuid

router = APIRouter()


@router.get("", response_model=List[EmergencyReportResponse])
async def list_reports(
    urgency: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(EmergencyReport)
    if urgency:
        stmt = stmt.where(EmergencyReport.urgency == urgency.upper())
    if category:
        stmt = stmt.where(EmergencyReport.category == category.upper())
    if status_filter:
        stmt = stmt.where(EmergencyReport.status == status_filter.upper())
    stmt = stmt.order_by(EmergencyReport.created_at.desc() if hasattr(EmergencyReport, 'created_at') else EmergencyReport.server_received_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("", response_model=EmergencyReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_in: EmergencyReportCreate,
    db: AsyncSession = Depends(get_db)
):
    # Automated AI Triage
    ml_result = classifier.predict(report_in.raw_text)

    # Use client provided values if explicit, else fallback to model predictions
    category = report_in.category if report_in.category != "OTHER" else ml_result["category"]
    urgency = report_in.urgency if report_in.urgency != "MEDIUM" else ml_result["urgency"]
    summary = f"Identified needs: {', '.join(ml_result['keywords'])}" if ml_result["keywords"] else None

    client_uuid = report_in.client_assigned_uuid or generate_uuid()
    now = get_utc_now()

    # Check duplicate
    dup_stmt = select(EmergencyReport).where(EmergencyReport.client_assigned_uuid == client_uuid)
    existing = (await db.execute(dup_stmt)).scalar_one_or_none()
    if existing:
        return existing

    report = EmergencyReport(
        client_assigned_uuid=client_uuid,
        reporter_name=report_in.reporter_name,
        contact_info=report_in.contact_info,
        latitude=report_in.latitude,
        longitude=report_in.longitude,
        address_hint=report_in.address_hint,
        category=category,
        urgency=urgency,
        status="SUBMITTED",
        raw_text=report_in.raw_text,
        ai_summary=summary,
        ai_confidence=ml_result["confidence"],
        client_created_at=report_in.client_created_at or now,
        server_received_at=now,
        version=1
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/{report_id}", response_model=EmergencyReportResponse)
async def get_report(report_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(EmergencyReport).where(EmergencyReport.id == report_id)
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Emergency report not found.")
    return report


@router.patch("/{report_id}", response_model=EmergencyReportResponse)
async def update_report_status(
    report_id: str,
    update_in: EmergencyReportUpdate,
    current_user: User = Depends(require_roles(["VOLUNTEER", "COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(EmergencyReport).where(EmergencyReport.id == report_id)
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Emergency report not found.")

    if update_in.base_version != report.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Version mismatch. Server is on version {report.version}."
        )

    if update_in.status:
        report.status = update_in.status.upper()
    if update_in.category:
        report.category = update_in.category.upper()
    if update_in.urgency:
        report.urgency = update_in.urgency.upper()
    if update_in.is_duplicate is not None:
        report.is_duplicate = update_in.is_duplicate
    if update_in.duplicate_of_report_id:
        report.duplicate_of_report_id = update_in.duplicate_of_report_id

    report.verified_by_user_id = current_user.id
    report.version += 1
    report.updated_at = get_utc_now()

    await db.commit()
    await db.refresh(report)
    return report


@router.get("/requests/all", response_model=List[AssistanceRequestResponse])
async def list_assistance_requests(db: AsyncSession = Depends(get_db)):
    stmt = select(AssistanceRequest).order_by(AssistanceRequest.priority_score.desc(), AssistanceRequest.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{report_id}/requests", response_model=AssistanceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_assistance_request(
    report_id: str,
    req_in: AssistanceRequestCreate,
    current_user: User = Depends(require_roles(["VOLUNTEER", "COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    # Verify report exists
    stmt = select(EmergencyReport).where(EmergencyReport.id == report_id)
    report = (await db.execute(stmt)).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Associated report not found.")

    req = AssistanceRequest(
        client_assigned_uuid=req_in.client_assigned_uuid or generate_uuid(),
        emergency_report_id=report_id,
        shelter_id=req_in.shelter_id,
        resource_type_id=req_in.resource_type_id,
        requested_quantity=req_in.requested_quantity,
        fulfilled_quantity=0.0,
        status="PENDING",
        priority_score=req_in.priority_score,
        version=1
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return req
