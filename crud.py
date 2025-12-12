# crud.py
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
import models
import schemas
import os


# --- ФУНКЦИИ ДЛЯ ЭКРАНА "ДАТЧИКИ" ---

def get_all_locations(db: Session) -> list[models.Location]:
    """Возвращает все локации для выпадающего списка кабинетов."""
    return db.query(models.Location).order_by(models.Location.name).all()

def get_sensors_by_location(db: Session, location_id: int) -> list[models.Sensor]:
    """
    Возвращает все датчики, привязанные к конкретной локации, 
    сразу подгружая тип датчика (для названия и единицы измерения).
    """
    sensors = (
        db.query(models.Sensor)
        .options(joinedload(models.Sensor.sensor_type))
        .filter(models.Sensor.location_id == location_id)
        .all()
    )
    return sensors

def get_last_measurement(db: Session, sensor_id: int) -> Optional[models.Measurement]:
    """Получает последнее измерение для одного датчика."""
    return db.query(models.Measurement)\
        .filter(models.Measurement.sensor_id == sensor_id)\
        .order_by(models.Measurement.timestamp.desc())\
        .first()

# --- АНАЛИТИКА (ГРАФИКИ) ---
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

# --- ПОЛЬЗОВАТЕЛИ (ДЛЯ UI) ---
def get_users_for_ui(db: Session) -> list[schemas.UserListDTO]:
    users = db.query(models.User).all()
    result = []
    for u in users:
        status_text = "Онлайн" if u.is_online else "Оффлайн"
        
        result.append(schemas.UserListDTO(
            id=str(u.id),
            name=u.full_name,
            role=u.role,
            status=status_text
        ))
    return result

# --- ИСТОРИЯ ДЕЙСТВИЙ (ДЛЯ UI) ---
def get_logs_for_ui(db: Session, limit: int = 20) -> list[schemas.ActionLogDTO]:
    logs = (
        db.query(models.ActionLog)
        .options(joinedload(models.ActionLog.user))
        .order_by(desc(models.ActionLog.timestamp))
        .limit(limit)
        .all()
    )

    result = []
    for log in logs:
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


# --- ФУНКЦИЯ ДЛЯ ГЕНЕРАЦИИ ОТЧЕТА ---

def calculate_report_data(db: Session, start_time: datetime, end_time: datetime):
    """
    Рассчитывает агрегированные данные для отчета по всем датчикам за период.
    Возвращает список словарей с агрегатами.
    """
    
    stats = db.query(
        models.Location.name.label("location_name"),
        models.Sensor.name.label("sensor_name"),
        models.SensorType.name.label("sensor_type"),
        func.avg(models.Measurement.value).label("avg_value"),
        func.min(models.Measurement.value).label("min_value"),
        func.max(models.Measurement.value).label("max_value")
    ).join(
        models.Measurement, models.Measurement.sensor_id == models.Sensor.id
    ).join(
        models.Location, models.Location.id == models.Sensor.location_id
    ).join(
        models.SensorType, models.SensorType.id == models.Sensor.sensor_type_id
    ).filter(
        models.Measurement.timestamp >= start_time,
        models.Measurement.timestamp < end_time
    ).group_by(
        models.Location.name,
        models.Sensor.name,
        models.SensorType.name
    ).all()
    
    report_data = []
    for row in stats:
        report_data.append({
            "location": row.location_name,
            "sensor": row.sensor_name,
            "type": row.sensor_type,
            "avg": round(row.avg_value, 2),
            "min": round(row.min_value, 2),
            "max": round(row.max_value, 2),
        })
        
    return report_data

def save_report_locally(file_path: str, content: str):
    """
    Сохраняет отчёт в локальную папку reports/.
    Возвращает относительный путь к файлу.
    """
    try:
        # Создаём папку reports/, если её нет
        os.makedirs("reports", exist_ok=True)
        
        # Полный путь к файлу
        full_path = os.path.join("reports", file_path)
        
        # Сохраняем файл с UTF-8 кодировкой
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"✅ Report saved: {full_path}")
        
        # Возвращаем путь для сохранения в БД
        return f"/reports/{file_path}"
        
    except Exception as e:
        print(f"❌ ERROR: Failed to save report: {e}")
        # Возвращаем фиктивный путь, чтобы приложение не упало
        return f"/reports/{file_path}"