from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.inventory import ResourceType, ShelterInventory
from app.models.user import User
from app.schemas.inventory import (
    ResourceTypeCreate, ResourceTypeResponse,
    ShelterInventoryResponse, InventoryDeltaRequest
)
from app.services.conflict_resolver import ConflictResolver
from app.api.v1.endpoints.auth import get_current_user, require_roles

router = APIRouter()


@router.get("/resource-types", response_model=List[ResourceTypeResponse])
async def list_resource_types(db: AsyncSession = Depends(get_db)):
    stmt = select(ResourceType).order_by(ResourceType.category, ResourceType.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/resource-types", response_model=ResourceTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_type(
    res_in: ResourceTypeCreate,
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ResourceType).where(ResourceType.code == res_in.code.upper())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Resource code already exists.")

    res_type = ResourceType(
        code=res_in.code.upper(),
        name=res_in.name,
        category=res_in.category.upper(),
        unit=res_in.unit.upper(),
        is_critical=res_in.is_critical
    )
    db.add(res_type)
    await db.commit()
    await db.refresh(res_type)
    return res_type


@router.get("/shelters/{shelter_id}", response_model=List[ShelterInventoryResponse])
async def get_shelter_inventory(shelter_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ShelterInventory).where(
        ShelterInventory.shelter_id == shelter_id
    ).options(selectinload(ShelterInventory.resource_type))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/delta")
async def apply_inventory_delta(
    delta_req: InventoryDeltaRequest,
    current_user: User = Depends(require_roles(["VOLUNTEER", "COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    status_res, resulting_ver, err = await ConflictResolver.apply_inventory_delta(
        db=db,
        shelter_id=delta_req.shelter_id,
        resource_type_code=delta_req.resource_type_code,
        delta=delta_req.delta,
        device_id="portal-direct-delta",
        client_timestamp=delta_req.client_timestamp,
        base_version=delta_req.base_version,
        user_id=current_user.id
    )

    if status_res == "REJECTED":
        raise HTTPException(status_code=400, detail=err or "Delta rejected.")

    return {
        "status": status_res,
        "resulting_version": resulting_ver,
        "shelter_id": delta_req.shelter_id,
        "resource_type_code": delta_req.resource_type_code,
        "applied_delta": delta_req.delta
    }
