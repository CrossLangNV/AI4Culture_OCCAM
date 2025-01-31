from fastapi import APIRouter

from app.api import tools, pipeline

api_router = APIRouter(prefix="/process")
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(tools.router, prefix="/tools", tags=["individual tools"])
