"""
FastAPI application for web interface.
"""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .routes import create_routes
from .service import APIService

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests for debugging and monitoring."""

    async def dispatch(self, request: Request, call_next):
        """
        Log HTTP request method and path before processing.

        Args:
            request (Request): FastAPI request object
            call_next: Next middleware or route handler in the chain

        Returns:
            Response: HTTP response from the next handler
        """
        logger.info(f"[HTTP] {request.method} {request.url.path}")
        response = await call_next(request)
        return response


def create_app(service: APIService) -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        service: APIService instance

    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="Agile Practice Prediction API",
        description="API for agile practice recommendations using collaborative filtering and sequence learning",
        version="1.0.0",
    )

    # Request logging middleware
    app.add_middleware(LoggingMiddleware)

    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routes
    router = create_routes(service)
    app.include_router(router)

    # Mount static files (frontend)
    web_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web")
    if os.path.exists(web_dir):
        app.mount("/static", StaticFiles(directory=os.path.join(web_dir, "static")), name="static")

        # Serve index.html at root
        @app.get("/")
        async def read_root():
            from fastapi.responses import FileResponse

            index_path = os.path.join(web_dir, "index.html")
            if os.path.exists(index_path):
                return FileResponse(index_path)
            return {"message": "Web interface not found. Please ensure web/index.html exists."}

    return app
