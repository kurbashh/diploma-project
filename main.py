from fastapi import FastAPI, Depends, HTTPException
from datetime import datetime
from sqlalchemy.orm import Session
from database import Base, SessionLocal, engine
import models
import schemas
from models import Metric


Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Microclimate Monitoring API",
    version="1.0.0"
)

def get_db():
    db = SessionLocal()
    try:
        yield db  # возвращаем сессию в обработчик эндпоинта
    finally:
        db.close()

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
# GET: список всех метрик
@app.get("/api/metrics", response_model=list[schemas.MetricRead])
def get_metrics(db: Session = Depends(get_db)):
    metrics = db.query(Metric).all()
    return metrics

# POST: добавление новой метрики
@app.post("/api/metrics", response_model=schemas.MetricRead)
def create_metric(metric: schemas.MetricCreate, db: Session = Depends(get_db)):
    db_metric = Metric(**metric.dict(), timestamp=datetime.utcnow())  # явный timestamp
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    return db_metric