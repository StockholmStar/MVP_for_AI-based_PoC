from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import CORS_ORIGINS, ensure_data_dirs
from app.services.storage import init_db


def create_app() -> FastAPI:
    ensure_data_dirs()
    init_db()
    app = FastAPI(title="AI Product Workspace API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
