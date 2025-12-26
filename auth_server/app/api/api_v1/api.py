from fastapi import APIRouter
from app.api.api_v1.endpoints import auth, users, admin, node, proxy, whitelist

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(node.router, prefix="/node", tags=["node"])
api_router.include_router(proxy.router, prefix="/proxy", tags=["proxy"])
api_router.include_router(whitelist.router, prefix="/whitelist", tags=["whitelist"])