import os
from pathlib import Path, PurePosixPath

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import Response

from backend.config import CORS_ORIGINS
from backend.routers import health, labels, topics

app = FastAPI(
    title="Legends NPoints",
    description="What parents care about — derived from Reddit parenting communities",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SPAStaticFiles(StaticFiles):
    """StaticFiles with a history-API fallback for client-side routes.

    `html=True` only serves index.html for directory paths, so a deep link
    like /labels/1 or a browser refresh on it would 404. Any extensionless
    path outside /api that does not match a real file gets index.html instead.
    Missing assets (paths with an extension) and unknown /api routes keep
    their 404 so a broken asset URL is never answered with HTML.
    """

    async def get_response(self, path: str, scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404 or not self._is_spa_route(path):
                raise
            return await super().get_response("index.html", scope)

    @staticmethod
    def _is_spa_route(path: str) -> bool:
        if path == "api" or path.startswith("api/"):
            return False
        return PurePosixPath(path).suffix == ""


app.include_router(health.router)
app.include_router(topics.router)
app.include_router(labels.router)

# Serve React build in production
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", SPAStaticFiles(directory=str(frontend_dist), html=True), name="frontend")
