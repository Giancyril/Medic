from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.alerts import router as alerts_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous SRE & Incident Response Agent watching Kubernetes clusters and Prometheus telemetry.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(alerts_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
        "simulation_mode": settings.SIMULATION_MODE,
    }

@app.get("/", tags=["system"])
async def root():
    return {
        "message": "Incident Response Agent API is running",
        "docs_url": "/docs",
        "health_url": "/health",
        "webhook_url": f"{settings.API_V1_PREFIX}/alerts/webhook"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
