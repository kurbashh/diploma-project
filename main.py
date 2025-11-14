from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="Microclimate Monitoring API",
    version="1.0.0"
)

@app.get("/api/status")
def get_status():
    return {
        "status": "ok",
        "server_time": datetime.utcnow(),
        "message": "API is running"
    }

@app.get("/api/data")
def get_data():
    # временные тестовые данные — позже заменим на реальные от датчиков
    return {
        "temperature": 23.5,
        "humidity": 45,
        "co2_level": 600,
        "light": 120,
        "timestamp": datetime.utcnow()
    }