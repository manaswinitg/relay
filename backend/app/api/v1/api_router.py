from fastapi import APIRouter
from app.api.v1.endpoints import auth, shelters, inventory, reports, sync, ml

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Access Control"])
api_router.include_router(shelters.router, prefix="/shelters", tags=["Shelter Management & Spatial Discovery"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Emergency Resource Tracking & Deltas"])
api_router.include_router(reports.router, prefix="/reports", tags=["Emergency Reports & Assistance Work-Orders"])
api_router.include_router(sync.router, prefix="/sync", tags=["Distributed Synchronization & Conflict Quarantine"])
api_router.include_router(ml.router, prefix="/ml", tags=["AI Triage & NLP Classification"])
