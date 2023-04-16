from fastapi import APIRouter

from src.routes.login import router as login_router
from src.routes.links import router as links_router


# -------------------------------------------------------------------------------------------------------------->
router = APIRouter()
# -------------------------------------------------------------------------------------------------------------->


# Machine Load Router
router.include_router(login_router)
router.include_router(links_router)

@router.get("/test")
async def test():
    return "Test"

