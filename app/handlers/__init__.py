from aiogram import Router
from app.handlers.common import router as common_router
from app.handlers.admin import router as admin_router
from app.handlers.client import router as client_router

router = Router()
router.include_router(common_router)
router.include_router(admin_router)
router.include_router(client_router)
