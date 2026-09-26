from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.api.alerts import router as alerts_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.remediation import router as remediation_router
from backend.app.api.runbooks import router as runbooks_router
from backend.app.api.copilot import router as copilot_router
from backend.app.api.postmortems import router as postmortems_router
from backend.app.api.telemetry import router as telemetry_router
from backend.app.api.topology import router as topology_router
from backend.app.api.prediction import router as prediction_router
from backend.app.api.grouping import router as grouping_router
from backend.app.api.oncall import router as oncall_router
from backend.app.api.canary import router as canary_router
from backend.app.api.resilience import router as resilience_router
from backend.app.api.audit import router as audit_router

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
app.include_router(incidents_router, prefix=settings.API_V1_PREFIX)
app.include_router(remediation_router, prefix=settings.API_V1_PREFIX)
app.include_router(runbooks_router, prefix=settings.API_V1_PREFIX)
app.include_router(copilot_router, prefix=settings.API_V1_PREFIX)
app.include_router(postmortems_router, prefix=settings.API_V1_PREFIX)
app.include_router(telemetry_router, prefix=settings.API_V1_PREFIX)
app.include_router(topology_router, prefix=settings.API_V1_PREFIX)
app.include_router(prediction_router, prefix=settings.API_V1_PREFIX)
app.include_router(grouping_router, prefix=settings.API_V1_PREFIX)
app.include_router(oncall_router, prefix=settings.API_V1_PREFIX)
app.include_router(canary_router, prefix=settings.API_V1_PREFIX)
app.include_router(resilience_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)

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
        "webhook_url": f"{settings.API_V1_PREFIX}/alerts/webhook",
        "incidents_url": f"{settings.API_V1_PREFIX}/incidents"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
