import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import calls, twilio_webhooks, forms
from app.services.session_manager import session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    logger.info("Starting Zappix Demo Backend...")
    settings = get_settings()
    logger.info(f"Environment: {settings.app_env}")
    yield
    logger.info("Shutting down Zappix Demo Backend...")
    await session_manager.close()


app = FastAPI(
    title="Zappix + Aldea AI Demo",
    description="Conversational AI Health Assessment Demo with LiveKit, Twilio, Deepgram, Cartesia, and OpenAI",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS (allow all origins for Twilio WebSocket connections)
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(calls.router)
app.include_router(twilio_webhooks.router)
app.include_router(forms.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Zappix + Aldea AI Demo API",
        "version": "1.0.0",
        "status": "healthy"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancer."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.app_debug
    )

