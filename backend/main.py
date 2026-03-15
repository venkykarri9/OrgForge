"""OrgForge FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.database import create_tables
from backend.core.cache import close_redis
from backend.api import auth, orgs, metadata, pipeline, deployments, git, ai

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield
    await close_redis()


app = FastAPI(
    title="OrgForge API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(orgs.router, prefix="/api/orgs", tags=["orgs"])
app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])
app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(deployments.router, prefix="/api/deployments", tags=["deployments"])
app.include_router(git.router, prefix="/api/git", tags=["git"])
app.include_router(ai.router, prefix="/api/ai", tags=["ai"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "orgforge-api"}
