from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

# Test Routers
from app.routers.test_llm import router as test_llm_router
from app.routers.test_sandbox import router as test_sandbox_router

# Core Pipeline Routers
from app.routers.scan import router as scan_router
from app.routers.fix import router as fix_router
from app.routers.verify import router as verify_router
from app.routers.report import router as report_router
from app.routers.websocket import router as websocket_router

app = FastAPI(
    title=settings.APP_NAME,
    description="CodeGuard AI agent backend - a11y scanner and remediation pipeline with NVIDIA Nemotron & Nebius Sandboxes",
    version="0.1.0",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Core Routers
app.include_router(scan_router)
app.include_router(fix_router)
app.include_router(verify_router)
app.include_router(report_router)
app.include_router(websocket_router)

# Smoke Test Routers
app.include_router(test_llm_router)
app.include_router(test_sandbox_router)


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
        "docs": "/docs",
        "test_endpoints": [
            "/test-llm/ultra",
            "/test-llm/nano",
            "/test-sandbox/echo",
        ],
        "pipeline_endpoints": [
            "/scan",
            "/fix",
            "/verify",
            "/report/{scan_id}",
            "/ws/progress",
        ],
    }
