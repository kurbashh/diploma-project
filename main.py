from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random # Для генерации тестовых данных
import crud # Импортируем наш новый файл
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

@app.get("/api/locations", response_model=List[schemas.LocationRead])
def get_locations(db: Session = Depends(get_db)):
    """Получить список всех локаций (кабинетов) для выпадающего списка."""
    return crud.get_all_locations(db)

# --- 1. ЭКРАН "ДАТЧИКИ" (Список и управление) ---

# [ИСПРАВЛЕНО] Старая функция get_sensors удаляется/заменяется на эту
@app.get("/api/sensors/{location_id}", response_model=List[schemas.SensorRead])
def get_sensors_by_location_id(location_id: int, db: Session = Depends(get_db)):
    """Получить список всех датчиков в конкретной локации (кабинете)."""
    
    sensors = crud.get_sensors_by_location(db, location_id)
    
    # Заполняем вычисляемое поле last_value
    result = []
    for sensor in sensors:
        last_measure = crud.get_last_measurement(db, sensor.id)
        
        # Создаем экземпляр Pydantic, вручную заполняя last_value
        sensor_data = schemas.SensorRead.from_orm(sensor)
        sensor_data.last_value = last_measure.value if last_measure else 0.0
        result.append(sensor_data)
        
    return result

# ... (update_sensor_settings остается почти без изменений) ...

@app.patch("/api/sensors/{sensor_id}", response_model=schemas.SensorRead)
def update_sensor_settings(sensor_id: int, update_data: schemas.SensorUpdate, db: Session = Depends(get_db)):
    """
    Управление датчиком: Включение/Выключение, Изменение целевого значения.
    """
    sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # ... (логика обновления данных) ...
        
    db.commit()
    db.refresh(sensor)
    
    # [Улучшено] Используем CRUD-функцию для получения последнего измерения
    last_measure = crud.get_last_measurement(db, sensor.id)

    # Создаем Pydantic схему для ответа, чтобы добавить last_value
    updated_sensor = schemas.SensorRead.from_orm(sensor)
    updated_sensor.last_value = last_measure.value if last_measure else 0.0
    
    return updated_sensor

# --- 2. ЭКРАН "АНАЛИЗ" (Графики) ---

@app.get("/api/history", response_model=List[schemas.MeasurementRead])
def get_history(sensor_id: int = None, db: Session = Depends(get_db)):
    """Данные для графика. Можно фильтровать по ID датчика."""
    query = db.query(models.Measurement)
    if sensor_id:
        query = query.filter(models.Measurement.sensor_id == sensor_id)
    
    # Берем последние 100 записей
    return query.order_by(models.Measurement.timestamp.desc()).limit(100).all()

# --- ДОБАВЛЯЕМ ЭНДПОИНТ ДЛЯ ЗАПИСИ НОВЫХ ПОКАЗАТЕЛЕЙ ---

@app.post("/api/measurements", status_code=status.HTTP_201_CREATED)
def record_measurement(
    measurement: schemas.MeasurementCreate, 
    db: Session = Depends(get_db)
):
    """Принимает новое измерение от скрипта-имитатора и записывает в базу."""
    
    # 1. Проверяем, существует ли указанный датчик
    sensor = db.query(models.Sensor).filter(models.Sensor.id == measurement.sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
        
    # 2. Создаем запись измерения
    # Используем данные из схемы: value, sensor_id. Timestamp генерируется базой.
    db_measurement = models.Measurement(
        sensor_id=measurement.sensor_id, 
        location_id=sensor.location_id, # Берем ID локации из объекта Sensor
        value=measurement.value,
        timestamp=datetime.utcnow()
    )
    
    db.add(db_measurement)
    db.commit()
    return {"status": "recorded", "value": measurement.value}

# --- 3. ЭКРАН "ПОЛЬЗОВАТЕЛИ" ---

# ВАЖНО: response_model изменен на UserListDTO
@app.get("/api/users", response_model=List[schemas.UserListDTO])
def get_users(db: Session = Depends(get_db)):
    """Возвращает список пользователей, отформатированный для UI"""
    return crud.get_users_for_ui(db)

# ВАЖНО: response_model изменен на ActionLogDTO
@app.get("/api/logs", response_model=List[schemas.ActionLogDTO])
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    """История действий, отформатированная для UI"""
    return crud.get_logs_for_ui(db, limit=limit)

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

# Добавили response_model=List[schemas.ChartPoint] для валидации
@app.get("/analytics/{sensor_id}", response_model=List[schemas.ChartPoint])
def read_analytics(sensor_id: int, days: int = 7, db: Session = Depends(get_db)):
    stats = crud.get_analytics_daily(db=db, sensor_id=sensor_id, days=days)
    if not stats:
        return []
    return stats