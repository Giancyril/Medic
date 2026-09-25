"""
Predictive Anomaly REST API.
Exposes endpoints for querying ML/statistical forecasts, time-to-failure (TTF), and imminent breach risks.
"""
from fastapi import APIRouter
from backend.prediction import prediction_engine

router = APIRouter(prefix="/prediction", tags=["prediction"])

@router.get("/forecasts", summary="Retrieve cluster-wide predictive anomaly and TTF forecasts")
async def get_forecasts():
    summary = prediction_engine.generate_cluster_predictions()
    return summary.model_dump()
