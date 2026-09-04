import os
import json
import joblib
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from dotenv import load_dotenv
from data_provider import MockLiveDataProvider, RealAPIDataProvider

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # adjust in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load artifacts
model = joblib.load("eta_model.pkl")
weather_encoder = joblib.load("weather_encoder.pkl")
with open("model_features.json") as f:
    features = json.load(f)
with open("routes.json") as f:
    routes = json.load(f)
with open("train_info.json") as f:
    train_info = json.load(f)

# Data provider
if os.getenv("USE_REAL_API", "false").lower() == "true":
    live_provider = RealAPIDataProvider()
else:
    live_provider = MockLiveDataProvider(routes, train_info)

# Pydantic model for delay report
class DelayReport(BaseModel):
    train_no: str
    station: str
    description: str = ""

# Store user reports (in-memory for hackathon)
user_reports = []

def predict_next_delay(current_features: dict) -> float:
    """Use model to predict delay at next station."""
    input_df = pd.DataFrame([current_features])
    # Ensure feature order matches training
    input_df = input_df[features]
    # Encode weather if needed
    if "weather" in input_df.columns:
        input_df["weather_encoded"] = weather_encoder.transform(input_df["weather"])
        input_df = input_df.drop(columns=["weather"])
    # Reorder columns to match model_features.json exactly
    input_df = input_df[features]
    pred = model.predict(input_df)[0]
    return max(0, pred)

@app.get("/api/trains")
def get_active_trains():
    return {"trains": live_provider.get_all_active_trains()}

@app.get("/api/train/{train_no}")
def get_train_full(train_no: str):
    status = live_provider.get_train_status(train_no)
    if status is None:
        raise HTTPException(404, "Train not active")
    # Add route info
    route_id = status["route_id"]
    route = routes[route_id]
    # Predict for next station
    current_delay_pred = predict_next_delay(status)
    status["predicted_delay_next"] = current_delay_pred
    status["route"] = route
    # Add source/destination
    status["source_station"] = route[0]["station"]
    status["destination_station"] = route[-1]["station"]
    return status

@app.get("/api/train/{train_no}/predict")
def get_prediction(train_no: str):
    status = live_provider.get_train_status(train_no)
    if status is None:
        raise HTTPException(404, "Train not active")
    pred = predict_next_delay(status)
    return {"train_no": train_no, "predicted_delay_minutes": pred}

@app.get("/api/admin/metrics")
def get_admin_metrics():
    # Placeholder metrics (in real system, compute on test set)
    return {
        "mae": 2.34,
        "rmse": 3.12,
        "accuracy_5min": 0.87
    }

@app.get("/api/admin/predictions")
def get_live_predictions():
    trains = live_provider.get_all_active_trains()
    predictions = []
    for t in trains:
        status = live_provider.get_train_status(t)
        pred = predict_next_delay(status)
        predictions.append({
            "train_no": t,
            "current_station": status["current_station"],
            "next_station": status["next_station"],
            "predicted_delay": pred,
            "actual_delay": status["current_delay"]  # simplified
        })
    return predictions

@app.post("/api/report-delay")
def report_delay(report: DelayReport):
    user_reports.append(report.dict())
    # Simple validation: if 3 reports for same train/station within 10 min, mark verified
    # For hackathon, just store and return count
    return {"message": "Report received", "total_reports": len(user_reports)}

@app.get("/api/admin/reports")
def get_reports():
    return user_reports

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)