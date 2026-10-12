from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analyses, auth, health, impact, repositories
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="CodeScope API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(repositories.router)
app.include_router(analyses.router)
app.include_router(impact.router)
