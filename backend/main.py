import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import firebase_admin

from backend.ml.model_loader import get_model_pipeline
from backend.api.router import router as api_router
from backend.api.accessibility import router as accessibility_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if not firebase_admin._apps:
            firebase_admin.initialize_app()
        logger.info("Firebase Admin initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin: {e}")

    yield
    get_model_pipeline.cache_clear()

app = FastAPI(title="Hyperlocal Command Center API", lifespan=lifespan)

# 1. Enable Global CORS Middleware with specific origins
origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",  # Create React App default
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(accessibility_router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
