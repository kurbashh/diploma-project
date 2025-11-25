from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random # Для генерации тестовых данных

# Импортируем наши обновленные файлы
import models
import schemas
from database import SessionLocal, engine

# Создаем таблицы (если их нет)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Microclimate Monitoring API")

# --- Dependency (Подключение к БД) ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 1. ЭКРАН "ДАТЧИКИ" (Список и управление) ---

@app.get("/api/sensors", response_model=List[schemas.SensorRead])
def get_sensors(db: Session = Depends(get_db)):
    """Получить список всех датчиков с их текущим статусом"""
    sensors = db.query(models.Sensor).all()
    

    for sensor in sensors:
        last_measure = db.query(models.Measurement)\
            .filter(models.Measurement.sensor_id == sensor.id)\
            .order_by(models.Measurement.timestamp.desc())\
            .first()
        sensor.last_value = last_measure.value if last_measure else 0.0
        
    return sensors

@app.patch("/api/sensors/{sensor_id}", response_model=schemas.SensorRead)
def update_sensor_settings(sensor_id: int, update_data: schemas.SensorUpdate, db: Session = Depends(get_db)):
    """
    Управление датчиком:
    - Включение/Выключение (is_active)
    - Изменение целевой температуры (target_value)
    """
    sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # Обновляем только те поля, которые пришли
    if update_data.is_active is not None:
        sensor.is_active = update_data.is_active
    if update_data.target_value is not None:
        sensor.target_value = update_data.target_value
        
    db.commit()
    db.refresh(sensor)
    
    # Добавляем last_value для корректного ответа по схеме
    last_measure = db.query(models.Measurement)\
        .filter(models.Measurement.sensor_id == sensor.id)\
        .order_by(models.Measurement.timestamp.desc())\
        .first()
    sensor.last_value = last_measure.value if last_measure else 0.0
    
    return sensor

# --- 2. ЭКРАН "АНАЛИЗ" (Графики) ---

@app.get("/api/history", response_model=List[schemas.MeasurementRead])
def get_history(sensor_id: int = None, db: Session = Depends(get_db)):
    """Данные для графика. Можно фильтровать по ID датчика."""
    query = db.query(models.Measurement)
    if sensor_id:
        query = query.filter(models.Measurement.sensor_id == sensor_id)
    
    # Берем последние 100 записей
    return query.order_by(models.Measurement.timestamp.desc()).limit(100).all()

# --- 3. ЭКРАН "ПОЛЬЗОВАТЕЛИ" ---

@app.get("/api/users", response_model=List[schemas.UserRead])
def get_users(db: Session = Depends(get_db)):
    return db.query(models.User).all()

@app.get("/api/logs", response_model=List[schemas.ActionLogRead])
def get_logs(db: Session = Depends(get_db)):
    """История входа"""
    logs = db.query(models.ActionLog).order_by(models.ActionLog.timestamp.desc()).limit(20).all()
    # Обогащаем именем пользователя
    for log in logs:
        log.user_name = log.user.full_name if log.user else "Unknown"
    return logs

# --- 4. ЭКРАН "ГЛАВНАЯ" (Уведомления) ---

@app.get("/api/notifications", response_model=List[schemas.NotificationRead])
def get_notifications(db: Session = Depends(get_db)):
    return db.query(models.Notification).filter(models.Notification.is_completed == False).all()

@app.post("/api/notifications/{notif_id}/complete")
def complete_notification(notif_id: int, db: Session = Depends(get_db)):
    """Нажать кнопку 'Выполнено'"""
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
    if notif:
        notif.is_completed = True
        db.commit()
    return {"status": "ok"}

# --- ВСПОМОГАТЕЛЬНЫЙ ЭНДПОИНТ (Для первого запуска) ---
@app.post("/api/seed_data")
def seed_database(db: Session = Depends(get_db)):
    """Создает тестовые данные, чтобы интерфейс не был пустым"""
    # 1. Типы
    t_temp = models.SensorType(name="Temperature", unit="°C")
    t_hum = models.SensorType(name="Humidity", unit="%")
    db.add_all([t_temp, t_hum])
    db.commit()
    
    # 2. Локации
    loc = models.Location(name="Main Workshop")
    db.add(loc)
    db.commit()
    
    # 3. Датчики
    s1 = models.Sensor(name="Main AC", location_id=loc.id, sensor_type_id=t_temp.id, target_value=20.0)
    s2 = models.Sensor(name="Humidifier", location_id=loc.id, sensor_type_id=t_hum.id, target_value=80.0)
    db.add_all([s1, s2])
    db.commit()
    
    # 4. Измерения (История)
    for i in range(50):
        m1 = models.Measurement(sensor_id=s1.id, location_id=loc.id, value=20 + random.uniform(-2, 2), timestamp=datetime.utcnow() - timedelta(hours=i))
        m2 = models.Measurement(sensor_id=s2.id, location_id=loc.id, value=50 + random.uniform(-5, 5), timestamp=datetime.utcnow() - timedelta(hours=i))
        db.add_all([m1, m2])
    
    # 5. Пользователи
    u1 = models.User(full_name="Kseniya Kruchina", role="engineer", is_online=True, hashed_password="xhz")
    db.add(u1)
    
    db.commit()
    return {"message": "Database seeded!"}