"""FastAPI Gateway Server for Orkit Crew."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.memory import memory_manager
from ..core.router import router
from .routes import api_router
from .websocket import websocket_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Orkit Crew Gateway Server...")
    logger.info(f"Available crews: {list(router.get_available_crews().keys())}")
    yield
    # Shutdown
    logger.info("Shutting down Orkit Crew Gateway Server...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Orkit Crew Gateway",
        description="FastAPI Gateway Server for Orkit Crew - Multi-Agent AI System",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Orkit Crew Gateway",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        stats = await memory_manager.get_stats()
        return {
            "status": "healthy",
            "memory_stats": stats,
        }

    return app


# Create the application instance
app = create_app()
