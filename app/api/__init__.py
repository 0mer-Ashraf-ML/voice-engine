from fastapi import APIRouter
from .auth import router as auth_router
from .assistants import router as assistants_router
from .calls import router as calls_router
from .phone_numbers import router as phone_numbers_router
from .squads import router as squads_router
from .tools import router as tools_router
from .users import router as users_router
from .usage import router as usage_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(assistants_router, prefix="/assistants", tags=["Assistants"])
api_router.include_router(calls_router, prefix="/calls", tags=["Calls"])
api_router.include_router(phone_numbers_router, prefix="/phone-numbers", tags=["Phone Numbers"])
api_router.include_router(squads_router, prefix="/squads", tags=["Squads"])
api_router.include_router(tools_router, prefix="/tools", tags=["Tools"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(usage_router, prefix="/usage", tags=["Usage"])