from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.db.database import Base, engine
from app.api.routes.health import router as health_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.data import router as data_router


settings = get_settings()
app = FastAPI(title="Amazi Scheduling API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.include_router(health_router, prefix="/api")
app.include_router(uploads_router, prefix="/api")
app.include_router(data_router, prefix="/api")

