from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.api.v1.api_router import api_router
from app.api.websockets import router as ws_router
from app.models import User, ResourceType, Shelter, ShelterInventory


async def seed_initial_data():
    """
    Seeds default administrative users, core emergency resource types,
    and simulated shelters for local testing and portfolio demonstrations.
    """
    async with AsyncSessionLocal() as session:
        # 1. Seed Roles/Users
        user_stmt = select(User).where(User.email == "coordinator@relay.org")
        coord = (await session.execute(user_stmt)).scalar_one_or_none()
        if not coord:
            admin_user = User(
                email="coordinator@relay.org",
                password_hash=get_password_hash("relay123"),
                full_name="Sarah Chen (Lead Coordinator)",
                role="COORDINATOR",
                phone="+1-555-019-2831"
            )
            volunteer_user = User(
                email="volunteer@relay.org",
                password_hash=get_password_hash("relay123"),
                full_name="Marcus Vance (Field Volunteer)",
                role="VOLUNTEER",
                phone="+1-555-019-9482"
            )
            citizen_user = User(
                email="citizen@relay.org",
                password_hash=get_password_hash("relay123"),
                full_name="David Miller (Citizen)",
                role="CITIZEN",
                phone="+1-555-019-4821"
            )
            session.add_all([admin_user, volunteer_user, citizen_user])
            await session.commit()

        # 2. Seed Standard Emergency Resource Catalog
        rt_stmt = select(ResourceType)
        existing_rts = (await session.execute(rt_stmt)).scalars().all()
        if not existing_rts:
            rts = [
                ResourceType(code="POTABLE_WATER", name="Clean Drinking Water", category="WATER", unit="LITERS", is_critical=True),
                ResourceType(code="MRE_RATIONS", name="Ready-to-Eat Meal Rations", category="FOOD", unit="MEALS", is_critical=True),
                ResourceType(code="FIRST_AID_KITS", name="Trauma & First Aid Kits", category="MEDICAL", unit="KITS", is_critical=True),
                ResourceType(code="BLANKETS_COTS", name="Emergency Blankets & Cots", category="SHELTER_SUPPLIES", unit="UNITS", is_critical=False),
                ResourceType(code="GENERATOR_FUEL", name="Emergency Power Diesel", category="POWER", unit="LITERS", is_critical=True),
                ResourceType(code="HYGIENE_KITS", name="Sanitation & Hygiene Packs", category="SANITATION", unit="KITS", is_critical=False),
            ]
            session.add_all(rts)
            await session.commit()

        # 3. Seed Initial Shelters if empty
        s_stmt = select(Shelter)
        existing_shelters = (await session.execute(s_stmt)).scalars().all()
        if not existing_shelters:
            # San Francisco Bay Area simulated coordinate cluster
            s1 = Shelter(
                name="Bayview Community Center Shelter",
                address="5000 3rd St, San Francisco, CA 94124",
                latitude=37.7312,
                longitude=-122.3892,
                total_capacity=150,
                current_occupancy=65,
                status="OPEN",
                contact_phone="+1-415-555-0101",
                version=1
            )
            s2 = Shelter(
                name="Mission Dolores Relief Gymnasium",
                address="3321 16th St, San Francisco, CA 94114",
                latitude=37.7645,
                longitude=-122.4278,
                total_capacity=220,
                current_occupancy=190,
                status="OPEN",
                contact_phone="+1-415-555-0102",
                version=1
            )
            s3 = Shelter(
                name="Marina Green Field Aid Station",
                address="Marina Blvd & Fillmore St, San Francisco, CA 94123",
                latitude=37.8055,
                longitude=-122.4385,
                total_capacity=80,
                current_occupancy=80,
                status="FULL",
                contact_phone="+1-415-555-0103",
                version=1
            )
            session.add_all([s1, s2, s3])
            await session.commit()

            # Seed shelter inventories
            rt_dict = {rt.code: rt.id for rt in (await session.execute(select(ResourceType))).scalars().all()}
            invs = [
                ShelterInventory(shelter_id=s1.id, resource_type_id=rt_dict["POTABLE_WATER"], quantity=800.0, min_threshold=100.0, version=1),
                ShelterInventory(shelter_id=s1.id, resource_type_id=rt_dict["MRE_RATIONS"], quantity=450.0, min_threshold=50.0, version=1),
                ShelterInventory(shelter_id=s1.id, resource_type_id=rt_dict["FIRST_AID_KITS"], quantity=40.0, min_threshold=10.0, version=1),
                ShelterInventory(shelter_id=s2.id, resource_type_id=rt_dict["POTABLE_WATER"], quantity=300.0, min_threshold=150.0, version=1),
                ShelterInventory(shelter_id=s2.id, resource_type_id=rt_dict["BLANKETS_COTS"], quantity=200.0, min_threshold=30.0, version=1),
            ]
            session.add_all(invs)
            await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure database schema exists
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed default data
    await seed_initial_data()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Research prototype for an Offline-First Emergency Resource Coordination System using Distributed Computing.",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(ws_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "mode": settings.ENVIRONMENT
    }
