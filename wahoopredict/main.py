"""
WAHOOPREDICT - Bittensor subnet for binary prediction markets. Odds, not oaths. Grift responsibly.

FastAPI application factory and routers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import orjson
from fastapi.responses import ORJSONResponse

from wahoopredict.config import settings
from wahoopredict.api.routes_events import router as events_router
from wahoopredict.api.routes_submit import router as submit_router
from wahoopredict.api.routes_public import router as public_router
from wahoopredict.api.routes_health import router as health_router
from wahoopredict.api.routes_affiliate import router as affiliate_router


def create_app() -> FastAPI:
    """
    Create FastAPI application.
    
    Returns:
        FastAPI app instance
    """
    app = FastAPI(
        title="WAHOOPREDICT",
        description="A Bittensor subnet for binary prediction markets. Miners submit probability predictions, validators score them using Brier scores.",
        version="0.1.0",
        default_response_class=ORJSONResponse
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(events_router)
    app.include_router(submit_router)
    app.include_router(public_router)
    app.include_router(health_router)
    app.include_router(affiliate_router)
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "WAHOOPREDICT",
            "version": "0.1.0",
            "description": "We reduce life to a button. Odds, not oaths. Grift responsibly.",
            "api": "https://wahoopredict.com/en/events"
        }
    
    return app


# Create app instance
app = create_app()

