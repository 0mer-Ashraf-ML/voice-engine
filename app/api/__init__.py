from fastapi import APIRouter
from . import users, auth, assistants, calls, phone_numbers, squads, tools, usage

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(assistants.router, prefix="/assistants", tags=["assistants"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(phone_numbers.router, prefix="/phone-numbers", tags=["phone-numbers"])
api_router.include_router(squads.router, prefix="/squads", tags=["squads"])
api_router.include_router(tools.router, prefix="/tools", tags=["tools"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
