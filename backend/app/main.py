from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import router as api_router
from backend.app.core.config import settings
from backend.app.database.session import Base, SessionLocal, engine
from backend.app.services.seed_service import seed_initial_pricing, seed_reference_data
from backend.app.sync.manager import sync_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_reference_data(db)
        await seed_initial_pricing(db)
    sync_manager.start_background_loop()
    yield
    await sync_manager.stop_background_loop()


app = FastAPI(
    title="MyAIStats API",
    description=(
        "Local-first AI API usage, actual vs. estimated costs, confirmed balances, "
        "and model pricing intelligence across providers."
    ),
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.version,
        "bind_host": settings.host,
    }
