# crud.py
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
import models
import schemas  # Импорт твоих моделей


# --- НОВЫЕ ФУНКЦИИ ДЛЯ ЭКРАНА "ДАТЧИКИ" ---

def get_all_locations(db: Session) -> list[models.Location]:
    """Возвращает все локации для выпадающего списка кабинетов."""
    return db.query(models.Location).order_by(models.Location.name).all()

def get_sensors_by_location(db: Session, location_id: int) -> list[models.Sensor]:
    """
    Возвращает все датчики, привязанные к конкретной локации, 
    сразу подгружая тип датчика (для названия и единицы измерения).
    """
    # Используем joinedload для SensorType, чтобы получить name и unit
    sensors = (
        db.query(models.Sensor)
        .options(joinedload(models.Sensor.sensor_type))
        .filter(models.Sensor.location_id == location_id)
        .all()
    )
    return sensors

# Дополнительно: функция для получения последнего значения (для оптимизации)
def get_last_measurement(db: Session, sensor_id: int) -> Optional[models.Measurement]:
    """Получает последнее измерение для одного датчика."""
    return db.query(models.Measurement)\
        .filter(models.Measurement.sensor_id == sensor_id)\
        .order_by(models.Measurement.timestamp.desc())\
        .first()

# --- 1. АНАЛИТИКА (ГРАФИКИ) ---
def get_analytics_daily(db: Session, sensor_id: int, days: int = 7):
    start_date = datetime.utcnow() - timedelta(days=days)
    results = (
        db.query(
            cast(models.Measurement.timestamp, Date).label("date"), 
            func.avg(models.Measurement.value).label("avg_value")
        )
        .filter(
            models.Measurement.sensor_id == sensor_id,
            models.Measurement.timestamp >= start_date
        )
        .group_by(cast(models.Measurement.timestamp, Date))
        .order_by(cast(models.Measurement.timestamp, Date))
        .all()
    )
    data = []
    for row in results:
        data.append({
            "label": row.date.strftime("%d.%m"), 
            "value": round(row.avg_value, 1)
        })
    return data

# --- 2. ПОЛЬЗОВАТЕЛИ (ДЛЯ UI) ---
def get_users_for_ui(db: Session) -> list[schemas.UserListDTO]:
    users = db.query(models.User).all()
    result = []
    for u in users:
        # Логика форматирования статуса
        status_text = "Онлайн" if u.is_online else "Оффлайн"
        
        result.append(schemas.UserListDTO(
            id=str(u.id),
            name=u.full_name,
            role=u.role,
            status=status_text
        ))
    return result

# --- 3. ИСТОРИЯ ДЕЙСТВИЙ (ДЛЯ UI) ---
def get_logs_for_ui(db: Session, limit: int = 20) -> list[schemas.ActionLogDTO]:
    logs = (
        db.query(models.ActionLog)
        .options(joinedload(models.ActionLog.user)) # Оптимизация запроса
        .order_by(desc(models.ActionLog.timestamp))
        .limit(limit)
        .all()
    )

    result = []
    for log in logs:
        # Логика форматирования времени
        time_str = log.timestamp.strftime("%H:%M:%S")
        
        user_name = log.user.full_name if log.user else "Unknown"
        user_role = log.user.role if log.user else "Unknown"

        result.append(schemas.ActionLogDTO(
            id=f"h{log.id}", 
            user=user_name,
            role=user_role,
            action=log.action,
            time=time_str
        ))
    return result