from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.customers import router as customers_router
from app.api.v1.fiscal import router as fiscal_router
from app.api.v1.health import router as health_router
from app.api.v1.hospitality import router as hospitality_router
from app.api.v1.payments import router as payments_router
from app.api.v1.pos import router as pos_router
from app.api.v1.procurement import router as procurement_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.warehouse import router as warehouse_router
from app.core.redis import close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(title="Griltek POS — Cloud API", version="0.1.0", lifespan=lifespan)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(warehouse_router, prefix="/api/v1")
app.include_router(procurement_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(pos_router, prefix="/api/v1")
app.include_router(fiscal_router, prefix="/api/v1")
app.include_router(hospitality_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": "Griltek POS Cloud", "version": "0.1.0"}
