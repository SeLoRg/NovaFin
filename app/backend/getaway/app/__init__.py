from fastapi import APIRouter
from getaway.app.auth.router import router as auth_router
from getaway.app.wallet_service.router import router as wallet_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(wallet_router, prefix="/wallet", tags=["wallet"])
