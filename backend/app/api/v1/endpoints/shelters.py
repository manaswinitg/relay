from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.shelter import Shelter
from app.models.inventory import ShelterInventory
from app.models.user import User
from app.schemas.shelter import ShelterCreate, ShelterUpdate, ShelterResponse, ShelterWithDistance
from app.schemas.inventory import ShelterInventoryResponse
from app.models.base import generate_uuid
from app.services.geo_service import haversine_distance, get_bounding_box
from app.services.conflict_resolver import ConflictResolver
from app.api.v1.endpoints.auth import get_current_user, require_roles

router = APIRouter()


@router.get("", response_model=List[ShelterResponse])
async def list_shelters(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Shelter)
    if status_filter:
        stmt = stmt.where(Shelter.status == status_filter.upper())
    stmt = stmt.order_by(Shelter.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/nearby", response_model=List[ShelterWithDistance])
async def find_nearby_shelters(
    latitude: float = Query(..., ge=-90.0, le=90.0),
    longitude: float = Query(..., ge=-180.0, le=180.0),
    radius_km: float = Query(50.0, gt=0.0, le=500.0),
    db: AsyncSession = Depends(get_db)
):
    min_lat, max_lat, min_lon, max_lon = get_bounding_box(latitude, longitude, radius_km)

    stmt = select(Shelter).where(
        Shelter.latitude >= min_lat,
        Shelter.latitude <= max_lat,
        Shelter.longitude >= min_lon,
        Shelter.longitude <= max_lon,
        Shelter.status != "CLOSED"
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    shelters_with_distance = []
    for s in candidates:
        dist = haversine_distance(latitude, longitude, s.latitude, s.longitude)
        if dist <= radius_km:
            s_dict = ShelterResponse.model_validate(s).model_dump()
            s_dict["distance_km"] = dist
            shelters_with_distance.append(ShelterWithDistance(**s_dict))

    # Sort ascending by distance
    shelters_with_distance.sort(key=lambda x: x.distance_km)
    return shelters_with_distance


@router.post("", response_model=ShelterResponse, status_code=status.HTTP_201_CREATED)
async def create_shelter(
    shelter_in: ShelterCreate,
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN", "VOLUNTEER"])),
    db: AsyncSession = Depends(get_db)
):
    shelter = Shelter(
        client_assigned_uuid=shelter_in.client_assigned_uuid or generate_uuid(),
        name=shelter_in.name,
        address=shelter_in.address,
        latitude=shelter_in.latitude,
        longitude=shelter_in.longitude,
        total_capacity=shelter_in.total_capacity,
        current_occupancy=shelter_in.current_occupancy,
        status=shelter_in.status.upper(),
        contact_phone=shelter_in.contact_phone,
        version=1
    )
    db.add(shelter)
    await db.commit()
    await db.refresh(shelter)
    return shelter


@router.get("/{shelter_id}", response_model=ShelterResponse)
async def get_shelter(shelter_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Shelter).where(Shelter.id == shelter_id)
    shelter = (await db.execute(stmt)).scalar_one_or_none()
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found.")
    return shelter


@router.put("/{shelter_id}", response_model=ShelterResponse)
async def update_shelter(
    shelter_id: str,
    update_in: ShelterUpdate,
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN", "VOLUNTEER"])),
    db: AsyncSession = Depends(get_db)
):
    payload = update_in.model_dump(exclude_unset=True, exclude={"base_version"})
    status_res, resulting_ver, msg = await ConflictResolver.evaluate_shelter_update(
        db=db,
        shelter_id=shelter_id,
        incoming_payload=payload,
        base_version=update_in.base_version,
        device_id="coordinator-web-portal",
        user_id=current_user.id
    )

    if status_res == "CONFLICT_ISOLATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflict detected! Server is on version {resulting_ver}. Discrepancy quarantined in coordinator triage."
        )
    elif status_res == "REJECTED":
        raise HTTPException(status_code=400, detail=msg or "Update rejected.")

    stmt = select(Shelter).where(Shelter.id == shelter_id)
    updated_shelter = (await db.execute(stmt)).scalar_one()
    return updated_shelter


@router.delete("/{shelter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelter(
    shelter_id: str,
    current_user: User = Depends(require_roles(["COORDINATOR", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Shelter).where(Shelter.id == shelter_id)
    shelter = (await db.execute(stmt)).scalar_one_or_none()
    if not shelter:
        raise HTTPException(status_code=404, detail="Shelter not found.")
    await db.delete(shelter)
    await db.commit()
