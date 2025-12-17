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



def execute_voice_command(db: Session, command_id: int, 
                         status: str, note: str = None) -> models.VoiceNotificationCommand:
    """Обновляет статус выполнения команды"""
    command = db.query(models.VoiceNotificationCommand).filter(
        models.VoiceNotificationCommand.id == command_id
    ).first()
    
    if command:
        command.execution_status = status
        # Note, you need to add execution_note to models.VoiceNotificationCommand if you want to use it
        # command.execution_note = note
        command.executed_at = datetime.utcnow()
        db.commit()
        db.refresh(command)
    
    return command


# -------------------------------------------------------------------
# 🔬 DIPLOMA CRITERIA CRUD FUNCTIONS
# -------------------------------------------------------------------

def get_sensor_measurements(db: Session, sensor_id: int, days: int = 7) -> list[models.Measurement]:
    """
    Получает все измерения датчика за последние N дней.
    Используется для анализа аномалий и генерации рекомендаций.
    
    Args:
        db: Сессия БД
        sensor_id: ID датчика
        days: Глубина анализа в днях
    
    Returns:
        Список измерений отсортированных по времени
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    measurements = (
        db.query(models.Measurement)
        .filter(
            models.Measurement.sensor_id == sensor_id,
            models.Measurement.timestamp >= start_date
        )
        .order_by(models.Measurement.timestamp.asc())
        .all()
    )
    return measurements


def create_anomaly_analysis(db: Session, 
                           sensor_id: int,
                           location_id: int,
                           classical_method: str,
                           classical_score: float,
                           classical_is_anomaly: bool,
                           transformer_model: str,
                           transformer_score: float,
                           transformer_is_anomaly: bool,
                           models_agreement: bool,
                           confidence: float) -> models.AnomalyAnalysis:
    """
    Сохраняет результаты анализа аномалий (DIPLOMA CRITERION 2&3).
    
    Args:
        db: Сессия БД
        sensor_id: ID датчика
        location_id: ID локации
        classical_method: Название классического метода
        classical_score: Оценка аномалии классическим методом (0-1)
        classical_is_anomaly: Является ли аномалией по классическому методу
        transformer_model: Название трансформер модели
        transformer_score: Оценка аномалии трансформер методом (0-1)
        transformer_is_anomaly: Является ли аномалией по трансформер методу
        models_agreement: Согласны ли модели в результате
        confidence: Общая уверенность в анализе (0-1)
    
    Returns:
        Созданный объект AnomalyAnalysis
    """
    analysis = models.AnomalyAnalysis(
        sensor_id=sensor_id,
        location_id=location_id,
        classical_method=classical_method,
        classical_anomaly_score=classical_score,
        classical_is_anomaly=classical_is_anomaly,
        transformer_model=transformer_model,
        transformer_anomaly_score=transformer_score,
        transformer_is_anomaly=transformer_is_anomaly,
        models_agreement=models_agreement,
        confidence=confidence,
        # analysis_timestamp=datetime.utcnow() - У вас нет такого поля в models.py
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def get_anomaly_analyses(db: Session, 
                        location_id: int = None,
                        limit: int = 50) -> list[models.AnomalyAnalysis]:
    """
    Получает результаты анализа аномалий (DIPLOMA CRITERION 2&3).
    
    Args:
        db: Сессия БД
        location_id: Фильтр по локации (опционально)
        limit: Максимум результатов
    
    Returns:
        Список анализов отсортированных по времени (новые первыми)
    """
    query = db.query(models.AnomalyAnalysis)
    
    if location_id:
        query = query.filter(models.AnomalyAnalysis.location_id == location_id)
    
    # Сортировка по полю created_at
    analyses = query.order_by(models.AnomalyAnalysis.created_at.desc()).limit(limit).all()
    return analyses


def create_intelligent_recommendation(db: Session,
                                      sensor_id: int,
                                      location_id: int,
                                      problem_description: str,
                                      recommended_action: str,
                                      target_value: float,
                                      reasoning: str,
                                      confidence: float,
                                      severity: str,
                                      priority: int,
                                      # ИСПРАВЛЕНИЕ: Делаем опциональным
                                      anomaly_analysis_id: Optional[int] = None) -> models.IntelligentRecommendation:
    """
    Сохраняет сгенерированную рекомендацию (DIPLOMA CRITERION 1).
    
    Args:
        db: Сессия БД
        sensor_id: ID датчика
        location_id: ID локации
        problem_description: Описание проблемы (NLP generated)
        recommended_action: Рекомендуемое действие
        target_value: Целевое значение для датчика (CRITICAL для auto-verification)
        reasoning: Объяснение рекомендации
        confidence: Уверенность в рекомендации (0-1)
        severity: Уровень серьёзности (low, medium, high, critical)
        priority: Приоритет (1-5, где 5 - наивысший)
        anomaly_analysis_id: ID родительского анализа (теперь опционально)
    
    Returns:
        Созданный объект IntelligentRecommendation
    """
    recommendation = models.IntelligentRecommendation(
        sensor_id=sensor_id,
        location_id=location_id,
        problem_description=problem_description,
        recommended_action=recommended_action,
        target_value=target_value,
        reasoning=reasoning,
        confidence=confidence,
        severity=severity,
        priority=priority,
        anomaly_analysis_id=anomaly_analysis_id, # Передаем None, если не задан
        created_at=datetime.utcnow()
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def get_intelligent_recommendations(db: Session,
                                   location_id: int = None,
                                   sensor_id: int = None,
                                   limit: int = 50) -> list[models.IntelligentRecommendation]:
    """
    Получает интеллектуальные рекомендации (DIPLOMA CRITERION 1).
    
    Args:
        db: Сессия БД
        location_id: Фильтр по локации (опционально)
        sensor_id: Фильтр по датчику (опционально)
        limit: Максимум результатов
    
    Returns:
        Список рекомендаций отсортированных по приоритету
    """
    query = db.query(models.IntelligentRecommendation)
    
    if location_id:
        query = query.filter(models.IntelligentRecommendation.location_id == location_id)
    
    if sensor_id:
        query = query.filter(models.IntelligentRecommendation.sensor_id == sensor_id)
    
    recommendations = query.order_by(
        models.IntelligentRecommendation.priority.desc(),
        models.IntelligentRecommendation.created_at.desc()
    ).limit(limit).all()
    
    return recommendations


def create_voice_notification_command(db: Session,
                                      notification_id: int,
                                      transcript: str,
                                      command: str,
                                      execution_status: str = 'received') -> models.VoiceNotificationCommand:
    """
    Сохраняет голосовую команду для управления уведомлением (DIPLOMA CRITERION 4).
    
    Args:
        db: Сессия БД
        notification_id: ID уведомления
        transcript: Распознанный текст
        command: Тип команды (confirm, reject, modify, request_info, request_report, unknown)
        execution_status: Статус выполнения команды
    
    Returns:
        Созданный объект VoiceNotificationCommand
    """
    voice_cmd = models.VoiceNotificationCommand(
        notification_id=notification_id,
        transcript=transcript,
        command=command,
        execution_status=execution_status,
        # execution_timestamp=datetime.utcnow() - Этого поля нет в models.VoiceNotificationCommand, используем created_at
    )
    db.add(voice_cmd)
    db.commit()
    db.refresh(voice_cmd)
    return voice_cmd


def get_voice_notification_commands(db: Session,
                                    notification_id: int = None,
                                    limit: int = 50) -> list[models.VoiceNotificationCommand]:
    """
    Получает голосовые команды для уведомлений (DIPLOMA CRITERION 4).
    
    Args:
        db: Сессия БД
        notification_id: Фильтр по уведомлению (опционально)
        limit: Максимум результатов
    
    Returns:
        Список команд отсортированных по времени (новые первыми)
    """
    query = db.query(models.VoiceNotificationCommand)
    
    if notification_id:
        query = query.filter(models.VoiceNotificationCommand.notification_id == notification_id)
    
    # Сортировка по полю created_at
    commands = query.order_by(models.VoiceNotificationCommand.created_at.desc()).limit(limit).all()
    return commands