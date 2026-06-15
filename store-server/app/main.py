from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.catalog import router as catalog_router
from app.api.v1.health import router as health_router
from app.api.v1.heartbeat import router as heartbeat_router
from app.api.v1.stock import router as stock_router
from app.api.v1.sync_routes import router as sync_router
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title="Griltek POS — Store Server (Edge)",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(stock_router, prefix="/api/v1")
app.include_router(sync_router, prefix="/api/v1")
app.include_router(heartbeat_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": "Griltek POS Store Server", "version": "0.1.0"}
