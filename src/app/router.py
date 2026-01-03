from fastapi import APIRouter

from app.modules.todos import router as todos_router

router = APIRouter(prefix="/api/v1")

router.include_router(todos_router)
