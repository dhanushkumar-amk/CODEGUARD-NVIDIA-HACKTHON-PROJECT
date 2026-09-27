from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="CodeGuard AI agent backend - a11y scanner and remediation pipeline with NVIDIA Nemotron & Nebius Sandboxes",
    version="0.1.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health-check endpoint confirming backend operational status."""
    return {"status": "ok"}


@app.get("/", tags=["Root"])
async def root():
    """Root info endpoint."""
    return {
        "message": "Welcome to CodeGuard API",
        "health": "/health",
        "docs": "/docs"
    }
