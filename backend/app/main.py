import logging
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings

# Core Pipeline Routers
from app.routers.scan import router as scan_router
from app.routers.fix import router as fix_router
from app.routers.verify import router as verify_router
from app.routers.report import router as report_router
from app.routers.websocket import router as websocket_router

# Test Routers
from app.routers.test_llm import router as test_llm_router
from app.routers.test_sandbox import router as test_sandbox_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="CodeGuard AI agent backend - a11y scanner and remediation pipeline with NVIDIA Nemotron & Nebius Sandboxes",
    version="0.1.0",
)

# -------------------------------------------------------------------------
# CORS Configuration
# -------------------------------------------------------------------------
# Permissive origin regex for Vercel / Netlify preview & production deployments (*.vercel.app, *.netlify.app)
# alongside explicitly configured allowed_origins (production domain + localhost ports)
ALLOWED_ORIGIN_REGEX = r"^https:\/\/.*(\.vercel\.app|\.netlify\.app)$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# Global Exception Handlers
# -------------------------------------------------------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Formats known HTTP exceptions into clean, consistent JSON."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error": exc.detail if isinstance(exc.detail, str) else "HTTP Error",
            "detail": exc.detail,
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler ensuring unhandled exceptions return clean JSON instead of stack traces."""
    logger.error(f"Unhandled error processing {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": 500,
            "error": "Internal Server Error",
            "detail": str(exc),
            "path": request.url.path,
        },
    )


# -------------------------------------------------------------------------
# Router Registrations
# -------------------------------------------------------------------------
app.include_router(scan_router, prefix="/api/scan")
app.include_router(fix_router, prefix="/api/fix")
app.include_router(verify_router, prefix="/api/verify")
app.include_router(report_router, prefix="/api/report")
app.include_router(websocket_router, prefix="/ws")

# Smoke Test Routers
app.include_router(test_llm_router)
app.include_router(test_sandbox_router)


# -------------------------------------------------------------------------
# Base Health & Root Endpoints
# -------------------------------------------------------------------------
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health-check endpoint confirming backend operational status."""
    return {"status": "ok"}


@app.get("/", tags=["Root"])
async def root():
    """Root info endpoint detailing registered API routes."""
    return {
        "message": "Welcome to CodeGuard API",
        "health": "/health",
        "docs": "/docs",
        "endpoints": {
            "start_scan": "POST /api/scan/start",
            "get_fixes": "GET /api/fix/{scan_id}",
            "get_verification": "GET /api/verify/{scan_id}",
            "get_report": "GET /api/report/{scan_id}",
            "websocket_progress": "WS /ws/{scan_id}",
        },
    }
