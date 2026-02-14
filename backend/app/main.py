"""
HealthGuard AI - Main FastAPI Application
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .api import auth_router, chat_router, health_router, feishu_router, memory_router
from .core.logging_config import setup_logging
from .middleware import RequestLoggingMiddleware

# Logger will be initialized after setup_logging() is called
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    setup_logging(settings)

    # Initialize user storage
    from .storage.user_storage import init_user_storage
    from .storage.local_storage import LocalStorage
    storage = LocalStorage(settings.local_storage_path)
    init_user_storage(storage)
    logger.info("User storage initialized")

    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Storage path: {settings.local_storage_path}")
    logger.info(f"Log level: {settings.log_level.upper()}")
    logger.info(f"Debug mode: {settings.debug}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered personal health assistant for insulin resistance management",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware (after CORS)
if settings.log_api_requests:
    app.add_middleware(RequestLoggingMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(health_router)
app.include_router(feishu_router)
app.include_router(memory_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "message": "Welcome to HealthGuard AI - Your Personal Health Assistant"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "storage": settings.storage_type,
        "version": settings.app_version
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
