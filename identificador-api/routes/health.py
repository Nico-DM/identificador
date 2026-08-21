from db.config import db_enabled
from fastapi import APIRouter
from storage import storage_enabled

router = APIRouter()


@router.get("/")
async def root():
    return {"status": "ok"}


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "persistence": "supabase" if db_enabled() else "memory",
        "file_upload": storage_enabled(),
    }
