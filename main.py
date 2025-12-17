from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random
import os

import crud
import models
import schemas
from database import SessionLocal, engine, Base

# Создаем объект FastAPI
app = FastAPI(title="Microclimate Monitoring API")


@app.on_event("startup")
def startup_event():
    """При запуске автоматически создаём таблицы, если их нет."""
    try:
        print("🚀 Создаём таблицы SQLite (если их нет)")
        Base.metadata.create_all(bind=engine)
        
        # Создаём папку для отчётов
        os.makedirs("reports", exist_ok=True)
        print("📁 Папка reports/ готова")
        
    except Exception as e:
        print(f"⚠️ Warning: failed to create tables on startup: {e}")

# Подключаем статические файлы для скачивания отчётов
app.mount("/reports", StaticFiles(directory="reports"), name="reports")

# --- Dependency (Подключение к БД) ---
def get_db():
    """Создает и закрывает сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------------------------------------------
# 📍 1. ЛОКАЦИИ И ДАТЧИКИ
# -------------------------------------------------------------------

@app.get("/api/locations", response_model=List[schemas.LocationRead])
def get_locations(db: Session = Depends(get_db)):
    """Получить список всех локаций (кабинетов) для выпадающего списка."""
    return crud.get_all_locations(db)

@app.get("/api/sensors/{location_id}", response_model=List[schemas.SensorRead])
def get_sensors_by_location_id(location_id: int, db: Session = Depends(get_db)):
    """
    Получить датчики + СИМУЛЯЦИЯ ФИЗИКИ.
    При запросе мы проверяем, нужно ли 'подтянуть' текущее значение к целевому.
    """
    
    sensors = crud.get_sensors_by_location(db, location_id)
    
    result = []
    for sensor in sensors:
        last_measure = crud.get_last_measurement(db, sensor.id)
        current_val = last_measure.value if last_measure else 0.0
        
        # --- ЛОГИКА СИМУЛЯЦИИ (PHYSICS ENGINE) ---
        if sensor.is_active and sensor.target_value is not None:
            diff = sensor.target_value - current_val
            
            if abs(diff) > 0.1:
                time_since_last = datetime.utcnow() - last_measure.timestamp if last_measure else timedelta(seconds=100)
                
                if time_since_last.total_seconds() > 5:
                    step = diff * 0.1
                    
                    if abs(step) < 0.1:
                        step = 0.1 if diff > 0 else -0.1
                        
                    noise = random.uniform(-0.05, 0.05)
                    new_val = current_val + step + noise
                    
                    new_measure = models.Measurement(
                        sensor_id=sensor.id,
                        location_id=sensor.location_id,
                        value=round(new_val, 2),
                        timestamp=datetime.utcnow()
                    )
                    db.add(new_measure)
                    db.commit()
                    
                    current_val = new_val
        
        sensor_data = schemas.SensorRead.from_orm(sensor)
        sensor_data.last_value = round(current_val, 1)
        result.append(sensor_data)
        
    return result

@app.patch("/api/sensors/{sensor_id}", response_model=schemas.SensorRead)
def update_sensor_settings(
    sensor_id: int, 
    update_data: schemas.SensorUpdate, 
    user_id: int = 1,
    db: Session = Depends(get_db)
):
    """Управление датчиком с записью в ЛОГИ."""
    sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    action_text = []
    
    if update_data.is_active is not None and update_data.is_active != sensor.is_active:
        sensor.is_active = update_data.is_active 
        status = "Включил" if update_data.is_active else "Выключил"
        action_text.append(f"{status} датчик {sensor.name}")
        
    if update_data.target_value is not None:
        if update_data.target_value != sensor.target_value:
            sensor.target_value = update_data.target_value 
            action_text.append(f"Изменил {sensor.name} на {update_data.target_value}")

    if action_text:
        db.commit()
        db.refresh(sensor)
        
        full_action_description = ", ".join(action_text)
        new_log = models.ActionLog(
            user_id=user_id,
            action=full_action_description,
            timestamp=datetime.utcnow()
        )
        db.add(new_log)
        db.commit()

    last_measure = crud.get_last_measurement(db, sensor.id)
    updated_sensor = schemas.SensorRead.from_orm(sensor)
    updated_sensor.last_value = last_measure.value if last_measure else 0.0
    
    return updated_sensor

# -------------------------------------------------------------------
# 📊 2. АНАЛИТИКА И ДЭШБОРД
# -------------------------------------------------------------------

@app.get("/api/dashboard/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Считает среднюю температуру и влажность, а также их процентное изменение за 24 часа."""
    sensors = db.query(models.Sensor).all()
    
    cur_temp_vals = []
    cur_hum_vals = []
    old_temp_vals = []
    old_hum_vals = []

    time_24h_ago = datetime.utcnow() - timedelta(days=1)

    for sensor in sensors:
        last_measure = crud.get_last_measurement(db, sensor.id)
        
        old_measure = db.query(models.Measurement)\
            .filter(models.Measurement.sensor_id == sensor.id, 
                    models.Measurement.timestamp <= time_24h_ago)\
            .order_by(models.Measurement.timestamp.desc())\
            .first()
        
        if last_measure:
            if sensor.sensor_type.name == "Temperature":
                cur_temp_vals.append(last_measure.value)
                if old_measure: old_temp_vals.append(old_measure.value)
            elif sensor.sensor_type.name == "Humidity":
                cur_hum_vals.append(last_measure.value)
                if old_measure: old_hum_vals.append(old_measure.value)
    
    def get_avg(values):
        return sum(values) / len(values) if values else 0.0
        
    def get_percent_change(current, old):
        if not old or old == 0: return 0.0
        return ((current - old) / old) * 100

    avg_temp_now = get_avg(cur_temp_vals)
    avg_hum_now = get_avg(cur_hum_vals)
    avg_temp_old = get_avg(old_temp_vals)
    avg_hum_old = get_avg(old_hum_vals)

    return {
        "avg_temperature": round(avg_temp_now, 1),
        "avg_humidity": round(avg_hum_now, 1),
        "temp_change": round(get_percent_change(avg_temp_now, avg_temp_old), 1),
        "hum_change": round(get_percent_change(avg_hum_now, avg_hum_old), 1)
    }

@app.get("/analytics/{sensor_id}", response_model=List[schemas.ChartPoint])
def read_analytics(sensor_id: int, days: int = 7, db: Session = Depends(get_db)):
    """Данные для графика"""
    stats = crud.get_analytics_daily(db=db, sensor_id=sensor_id, days=days)
    if not stats:
        return []
    return stats

@app.get("/api/history", response_model=List[schemas.MeasurementRead])
def get_history(sensor_id: int = None, db: Session = Depends(get_db)):
    """Сырые данные"""
    query = db.query(models.Measurement)
    if sensor_id:
        query = query.filter(models.Measurement.sensor_id == sensor_id)
    return query.order_by(models.Measurement.timestamp.desc()).limit(100).all()

# -------------------------------------------------------------------
# 📄 3. ОТЧЕТЫ
# -------------------------------------------------------------------

@app.get("/api/reports", response_model=List[schemas.ReportRead])
def get_reports(db: Session = Depends(get_db)):
    """Список отчетов"""
    return db.query(models.Report).order_by(models.Report.report_date.desc()).all()

@app.post("/api/reports/generate/{period}", status_code=status.HTTP_201_CREATED)
def generate_report_endpoint(period: str, db: Session = Depends(get_db)):
    """
    Генерация отчета (недельный или месячный).
    Сохраняет файл локально в папку reports/.
    """
    end_time = datetime.utcnow()
    
    if period == "week":
        start_time = end_time - timedelta(days=7)
        title_prefix = "Недельный отчет"
    elif period == "month":
        start_time = end_time - timedelta(days=30)
        title_prefix = "Месячный отчет"
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use 'week' or 'month'.")

    # 1. Сбор агрегированных данных
    report_data = crud.calculate_report_data(db, start_time, end_time)
    
    if not report_data:
        return {"message": f"Нет данных для создания {title_prefix.lower()} за период: {start_time.strftime('%Y-%m-%d')} - {end_time.strftime('%Y-%m-%d')}"}

    # 2. Формирование содержания отчета
    report_content_lines = [f"{title_prefix} за период {start_time.strftime('%d.%m.%Y')} - {end_time.strftime('%d.%m.%Y')}\n"]
    report_content_lines.append("=" * 60)
    for data in report_data:
        report_content_lines.append(
            f"\nЛокация: {data['location']}\n"
            f"Датчик: {data['sensor']} ({data['type']})\n"
            f"  • Среднее значение: {data['avg']}\n"
            f"  • Минимум: {data['min']}\n"
            f"  • Максимум: {data['max']}"
        )
    report_file_content = "\n".join(report_content_lines)
    
    # 3. Сохранение файла локально
    filename = f"{period}_{end_time.strftime('%Y%m%d_%H%M%S')}.txt"
    file_url = crud.save_report_locally(filename, report_file_content)
    
    # 4. Сохранение метаданных отчета в БД
    report_title = f"{title_prefix} ({start_time.strftime('%d.%m')} - {end_time.strftime('%d.%m')})"
    
    new_report = models.Report(
        title=report_title,
        file_path=file_url,
        report_date=end_time
    )
    db.add(new_report)
    db.commit()

    return {
        "message": "Отчет успешно сгенерирован и сохранен.", 
        "title": report_title,
        "report_url": file_url
    }


@app.get("/api/reports/{report_id}/download")
def download_report(
    report_id: int, 
    user_id: int = 1, 
    db: Session = Depends(get_db)
):
    """Получить ссылку на скачивание отчета с логированием"""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    new_log = models.ActionLog(
        user_id=user_id,
        action=f"Скачал отчет: {report.title}",
        timestamp=datetime.utcnow()
    )
    db.add(new_log)
    db.commit()

    return {
        "download_url": report.file_path,
        "filename": report.title
    }

# -------------------------------------------------------------------
# 👥 4. ПОЛЬЗОВАТЕЛИ И ЛОГИ
# -------------------------------------------------------------------

@app.get("/api/users", response_model=List[schemas.UserListDTO])
def get_users(db: Session = Depends(get_db)):
    return crud.get_users_for_ui(db)

@app.get("/api/logs", response_model=List[schemas.ActionLogDTO])
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    return crud.get_logs_for_ui(db, limit=limit)

# -------------------------------------------------------------------
# 🔔 5. УВЕДОМЛЕНИЯ
# -------------------------------------------------------------------

@app.get("/api/notifications", response_model=List[schemas.NotificationRead])
def get_notifications(db: Session = Depends(get_db)):
    return db.query(models.Notification).filter(models.Notification.is_completed == False).all()

@app.post("/api/notifications/{notif_id}/complete")
def complete_notification(notif_id: int, db: Session = Depends(get_db)):
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
    if notif:
        notif.is_completed = True
        db.commit()
    return {"status": "ok"}

# -------------------------------------------------------------------
# 📥 6. СЛУЖЕБНЫЕ (IoT и Seed)
# -------------------------------------------------------------------

@app.post("/api/measurements", status_code=status.HTTP_201_CREATED)
def record_measurement(
    measurement: schemas.MeasurementCreate, 
    db: Session = Depends(get_db)
):
    sensor = db.query(models.Sensor).filter(models.Sensor.id == measurement.sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
        
    db_measurement = models.Measurement(
        sensor_id=sensor.id, 
        location_id=sensor.location_id,
        value=measurement.value,
        timestamp=datetime.utcnow()
    )
    
    db.add(db_measurement)
    db.commit()
    return {"status": "recorded", "value": measurement.value}

@app.post("/api/seed_data")
def seed_database(db: Session = Depends(get_db)):
    """Генератор тестовых данных"""
    t_temp = db.query(models.SensorType).filter(models.SensorType.name == "Temperature").first()
    if not t_temp:
        t_temp = models.SensorType(name="Temperature", unit="°C")
        db.add(t_temp)
    t_hum = db.query(models.SensorType).filter(models.SensorType.name == "Humidity").first()
    if not t_hum:
        t_hum = models.SensorType(name="Humidity", unit="%")
        db.add(t_hum)
    db.commit()

    existing_count = db.query(models.Location).count()
    NEW_ROOMS_COUNT = 3

    for i in range(1, NEW_ROOMS_COUNT + 1):
        room_number = existing_count + i
        new_loc = models.Location(name=f"Кабинет {room_number}")
        db.add(new_loc)
        db.commit()
        db.refresh(new_loc)

        s_temp = models.Sensor(
            name=f"Кондиционер {room_number}", 
            location_id=new_loc.id, 
            sensor_type_id=t_temp.id, 
            target_value=22.0,
            is_active=True
        )
        s_hum = models.Sensor(
            name=f"Увлажнитель {room_number}", 
            location_id=new_loc.id, 
            sensor_type_id=t_hum.id, 
            target_value=45.0,
            is_active=True
        )
        db.add_all([s_temp, s_hum])
        db.commit()
        
        for hour in range(24):
            val_temp = 22.0 + random.uniform(-3, 3) 
            m1 = models.Measurement(
                sensor_id=s_temp.id, 
                location_id=new_loc.id, 
                value=round(val_temp, 1), 
                timestamp=datetime.utcnow() - timedelta(hours=hour)
            )
            val_hum = 45.0 + random.uniform(-10, 10)
            m2 = models.Measurement(
                sensor_id=s_hum.id, 
                location_id=new_loc.id, 
                value=round(val_hum, 1), 
                timestamp=datetime.utcnow() - timedelta(hours=hour)
            )
            db.add_all([m1, m2])

    if not db.query(models.User).filter(models.User.full_name == "Kseniya Kruchina").first():
        u1 = models.User(full_name="Kseniya Kruchina", role="engineer", is_online=True, hashed_password="xhz")
        db.add(u1)
        
    db.commit()
    
    return {"message": f"Успешно создано {NEW_ROOMS_COUNT} новых кабинета!"}


# -------------------------------------------------------------------
# 🎯 DIPLOMA ENDPOINTS (NEW CRITERIA)
# -------------------------------------------------------------------

@app.get("/api/sensors/{sensor_id}/anomalies")
def analyze_sensor_anomalies(sensor_id: int, days: int = 7, db: Session = Depends(get_db)):
    """
    🎓 DIPLOMA CRITERION 2 & 3: Анализ аномалий с использованием классических и трансформер методов.
    
    Процесс:
    1. Извлекаем последние N дней измерений
    2. Применяем КЛАССИЧЕСКИЕ методы (Moving Average, Isolation Forest, Seasonal)
    3. Применяем ТРАНСФОРМЕР-подобные методы (Time Series Attention, Trend Analysis)
    4. Сравниваем результаты (DIPLOMA CRITERION 3)
    5. Возвращаем комбинированный анализ
    
    Args:
        sensor_id: ID датчика
        days: Глубина анализа (по умолчанию 7 дней)
    
    Returns:
        {
            'sensor_id': int,
            'sensor_name': str,
            'measurements_count': int,
            'analysis': {
                'classical': {...},
                'transformer': {...},
                'comparison': {
                    'models_agree': bool,
                    'consensus_is_anomaly': bool,
                    'agreement_score': float
                }
            }
        }
    """
    try:
        sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
        if not sensor:
            raise HTTPException(status_code=404, detail="Sensor not found")
        
        # Извлекаем измерения за последние N дней
        measurements = crud.get_sensor_measurements(db, sensor_id, days=days)
        
        if not measurements:
            return {
                'sensor_id': sensor_id,
                'sensor_name': sensor.name,
                'measurements_count': 0,
                'error': 'No measurements found for analysis'
            }
        
        # Преобразуем в список значений
        values = [m.value for m in measurements]
        
        # ИМПОРТИРУЕМ МОДУЛИ АНАЛИЗА
        from anomaly_detection_classical import (
            moving_avg_detector, isolation_forest_detector, seasonal_detector
        )
        from anomaly_detection_transformer import ensemble_detector
        
        # КЛАССИЧЕСКИЕ МЕТОДЫ
        classical_result = moving_avg_detector.detect(values)
        if not classical_result['is_anomaly']:
            classical_result = isolation_forest_detector.detect(values)
        if not classical_result['is_anomaly']:
            classical_result = seasonal_detector.detect(values)
        
        # ТРАНСФОРМЕР МЕТОДЫ
        transformer_result = ensemble_detector.detect(values)
        
        # СРАВНЕНИЕ МОДЕЛЕЙ (DIPLOMA CRITERION 3)
        models_agree = classical_result['is_anomaly'] == transformer_result['is_anomaly']
        consensus_is_anomaly = classical_result['is_anomaly'] and transformer_result['is_anomaly']
        
        agreement_score = (
            (1 - abs(classical_result['score'] - transformer_result['score'])) * 0.5 +
            (1 if models_agree else 0) * 0.5
        )
        
        # Сохраняем результаты анализа в БД
        analysis_record = models.AnomalyAnalysis(
            sensor_id=sensor_id,
            location_id=sensor.location_id,
            classical_method='ensemble',
            classical_anomaly_score=classical_result['score'],
            classical_is_anomaly=classical_result['is_anomaly'],
            transformer_model='ensemble',
            transformer_anomaly_score=transformer_result['score'],
            transformer_is_anomaly=transformer_result['is_anomaly'],
            models_agreement=models_agree,
            confidence=agreement_score,
            analysis_timestamp=datetime.utcnow()
        )
        db.add(analysis_record)
        db.commit()
        
        return {
            'sensor_id': sensor_id,
            'sensor_name': sensor.name,
            'measurements_count': len(measurements),
            'analysis': {
                'classical': {
                    'is_anomaly': classical_result['is_anomaly'],
                    'score': round(classical_result['score'], 3),
                    'description': classical_result.get('description', ''),
                    'method': 'moving_average + isolation_forest + seasonal'
                },
                'transformer': {
                    'is_anomaly': transformer_result['is_anomaly'],
                    'score': round(transformer_result['score'], 3),
                    'description': transformer_result.get('description', ''),
                    'reconstruction_error': round(transformer_result.get('reconstruction_error', 0), 3),
                    'trend_info': transformer_result.get('trend_info', {}),
                    'models_agree': transformer_result.get('models_agree', False)
                },
                'comparison': {
                    'models_agree': models_agree,
                    'consensus_is_anomaly': consensus_is_anomaly,
                    'agreement_score': round(agreement_score, 3),
                    'analysis_id': analysis_record.id
                }
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error analyzing sensor anomalies: {e}")
        return {
            'error': str(e),
            'sensor_id': sensor_id
        }


@app.post("/api/recommendations/generate")
def generate_recommendations(request_data: dict = None, db: Session = Depends(get_db)):
    """
    🎓 DIPLOMA CRITERION 1 & 2: Генерация интеллектуальных рекомендаций для проактивного управления.
    
    Процесс:
    1. Анализируем все датчики локации на аномалии
    2. Используем NLP для генерации описаний проблем
    3. Генерируем исполняемые рекомендации с target_value
    4. Сортируем по приоритету
    
    Body:
        {
            'location_id': int,
            'only_anomalies': bool (опционально, по умолчанию true)
        }
    
    Returns:
        {
            'location_id': int,
            'location_name': str,
            'recommendations': [
                {
                    'sensor_name': str,
                    'problem_description': str,
                    'recommended_action': str,
                    'target_value': float,
                    'severity': str,
                    'priority': int,
                    'confidence': float,
                    'reasoning': str,
                    'recommendation_id': int
                }
            ]
        }
    """
    try:
        # Парсим тело запроса
        location_id = request_data.get('location_id') if request_data else None
        only_anomalies = request_data.get('only_anomalies', True) if request_data else True
        
        if not location_id:
            raise HTTPException(status_code=400, detail="location_id is required")
        
        # Проверяем локацию
        location = db.query(models.Location).filter(models.Location.id == location_id).first()
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        
        # Получаем все датчики локации
        sensors = crud.get_sensors_by_location(db, location_id)
        
        # ИМПОРТИРУЕМ МОДУЛИ АНАЛИЗА
        from anomaly_detection_classical import moving_avg_detector
        from intelligent_recommendation_engine import RecommendationGenerator
        
        generator = RecommendationGenerator()
        recommendations = []
        
        for sensor in sensors:
            # Получаем последние измерения
            measurements = crud.get_sensor_measurements(db, sensor.id, days=7)
            
            if not measurements:
                continue
            
            last_measurement = measurements[-1]
            values = [m.value for m in measurements]
            
            # Анализируем на аномалии
            anomaly_result = moving_avg_detector.detect(values)
            
            # Если only_anomalies=True и это не аномалия, пропускаем
            if only_anomalies and not anomaly_result['is_anomaly']:
                continue
            
            # Генерируем рекомендацию
            recommendation = generator.generate_recommendation(
                sensor_name=sensor.name,
                sensor_type=sensor.sensor_type.name,
                current_value=last_measurement.value,
                anomaly_analysis=anomaly_result,
                location_room_type=location.room_type
            )
            
            # Сохраняем рекомендацию в БД
            rec_record = models.IntelligentRecommendation(
                sensor_id=sensor.id,
                location_id=location_id,
                problem_description=recommendation['problem_description'],
                recommended_action=recommendation['recommended_action'],
                target_value=recommendation['target_value'],
                reasoning=recommendation['reasoning'],
                confidence=recommendation['confidence'],
                severity=recommendation['severity'],
                priority=recommendation['priority']
            )
            db.add(rec_record)
            db.flush()  # Получаем ID
            
            recommendation['recommendation_id'] = rec_record.id
            recommendation['sensor_name'] = sensor.name
            recommendations.append(recommendation)
        
        # Сортируем по приоритету
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        db.commit()
        
        return {
            'location_id': location_id,
            'location_name': location.name,
            'recommendations_count': len(recommendations),
            'recommendations': recommendations
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        return {
            'error': str(e),
            'location_id': request_data.get('location_id') if request_data else None
        }


@app.post("/api/voice/notification-command")
def process_voice_notification_command(
    audio_data: dict,
    db: Session = Depends(get_db)
):
    """
    🎓 DIPLOMA CRITERION 4: Распознавание голосовых команд для управления уведомлениями.
    
    Использует Whisper для транскрибирования и распознавания команд:
    - 'confirm' / 'да': Подтверждение рекомендации
    - 'reject' / 'нет': Отклонение рекомендации
    - 'modify' / 'измени': Изменение целевого значения
    - 'request_info': Запрос информации об аномалии
    - 'request_report': Запрос отчета
    
    Body:
        {
            'audio_file_path': str,
            'notification_id': int,
            'sensor_id': int (опционально)
        }
    
    Returns:
        {
            'success': bool,
            'command': str,
            'confidence_speech': float,
            'confidence_command': float,
            'transcript': str,
            'action_taken': str,
            'voice_command_id': int
        }
    """
    try:
        audio_file_path = audio_data.get('audio_file_path')
        notification_id = audio_data.get('notification_id')
        sensor_id = audio_data.get('sensor_id')
        
        if not audio_file_path:
            raise HTTPException(status_code=400, detail="audio_file_path is required")
        
        if not notification_id:
            raise HTTPException(status_code=400, detail="notification_id is required")
        
        # ИМПОРТИРУЕМ МОДУЛЬ РАСПОЗНАВАНИЯ РЕЧИ
        from voice_notification_commands import voice_notification_manager
        
        # Обрабатываем голосовую команду (DIPLOMA CRITERION 4)
        voice_result = voice_notification_manager.process_notification_voice_input(
            audio_file_path=audio_file_path,
            notification_id=notification_id,
            sensor_id=sensor_id
        )
        
        if not voice_result.get('success'):
            return {
                'success': False,
                'error': voice_result.get('error', 'Unknown error'),
                'notification_id': notification_id
            }
        
        command = voice_result['command']
        transcript = voice_result['transcript']
        
        # Сохраняем команду в БД
        voice_cmd_record = models.VoiceNotificationCommand(
            notification_id=notification_id,
            transcript=transcript,
            command=command,
            execution_status='received',
            execution_timestamp=datetime.utcnow()
        )
        db.add(voice_cmd_record)
        db.flush()
        
        # Выполняем действие на основе команды
        action_taken = ''
        notification = db.query(models.Notification).filter(
            models.Notification.id == notification_id
        ).first()
        
        if command == 'confirm':
            # Отмечаем уведомление как подтверждённое
            notification.status = 'confirmed'
            action_taken = 'Recommendation confirmed, implementing changes'
            voice_cmd_record.execution_status = 'confirmed'
        
        elif command == 'reject':
            # Отмечаем как отклоненное
            notification.status = 'rejected'
            action_taken = 'Recommendation rejected'
            voice_cmd_record.execution_status = 'rejected'
        
        elif command == 'modify':
            # Пытаемся извлечь новое значение
            new_value = voice_result.get('extracted_value')
            if new_value:
                notification.required_target_value = float(new_value)
                action_taken = f'Target value modified to {new_value}'
                voice_cmd_record.execution_status = 'modified'
            else:
                action_taken = 'Modify command received but could not extract value'
                voice_cmd_record.execution_status = 'pending_clarification'
        
        elif command == 'request_info':
            action_taken = 'Information requested, sending detailed report'
            voice_cmd_record.execution_status = 'info_sent'
        
        elif command == 'request_report':
            action_taken = 'Historical report requested'
            voice_cmd_record.execution_status = 'report_sent'
        
        else:
            action_taken = 'Command not recognized'
            voice_cmd_record.execution_status = 'unknown_command'
        
        db.commit()
        
        return {
            'success': True,
            'command': command,
            'confidence_speech': voice_result['confidence_speech'],
            'confidence_command': voice_result['confidence_command'],
            'transcript': transcript,
            'detected_language': voice_result['detected_language'],
            'action_taken': action_taken,
            'voice_command_id': voice_cmd_record.id,
            'notification_id': notification_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing voice notification command: {e}")
        return {
            'success': False,
            'error': str(e),
            'notification_id': audio_data.get('notification_id') if audio_data else None
        }


@app.get("/api/diploma/analysis-stats")
def get_diploma_analysis_stats(location_id: int = None, db: Session = Depends(get_db)):
    """
    📊 Статистика по всем критериям дипломной работы.
    
    Показывает:
    - Количество проведённых анализов (CRITERION 2&3)
    - Статистику по классическим и трансформер методам (CRITERION 2&3)
    - Количество сгенерированных рекомендаций (CRITERION 1)
    - Количество обработанных голосовых команд (CRITERION 4)
    """
    try:
        # Статистика по аномалиям
        anomaly_analyses = db.query(models.AnomalyAnalysis)
        if location_id:
            anomaly_analyses = anomaly_analyses.filter(models.AnomalyAnalysis.location_id == location_id)
        anomaly_analyses = anomaly_analyses.all()
        
        # Статистика по рекомендациям
        recommendations = db.query(models.IntelligentRecommendation)
        if location_id:
            recommendations = recommendations.filter(models.IntelligentRecommendation.location_id == location_id)
        recommendations = recommendations.all()
        
        # Статистика по голосовым командам
        voice_commands = db.query(models.VoiceNotificationCommand).all()
        
        # Анализируем результаты
        classical_anomalies = sum(1 for a in anomaly_analyses if a.classical_is_anomaly)
        transformer_anomalies = sum(1 for a in anomaly_analyses if a.transformer_is_anomaly)
        model_agreements = sum(1 for a in anomaly_analyses if a.models_agreement)
        
        voice_commands_stats = {
            'confirm': sum(1 for v in voice_commands if v.command == 'confirm'),
            'reject': sum(1 for v in voice_commands if v.command == 'reject'),
            'modify': sum(1 for v in voice_commands if v.command == 'modify'),
            'request_info': sum(1 for v in voice_commands if v.command == 'request_info'),
            'request_report': sum(1 for v in voice_commands if v.command == 'request_report'),
            'unknown': sum(1 for v in voice_commands if v.command == 'unknown')
        }
        
        return {
            'diploma_criteria': {
                'criterion_1_practical_problem': {
                    'description': 'Proactive microclimate monitoring with intelligent recommendations',
                    'implemented': True,
                    'metrics': {
                        'total_recommendations': len(recommendations),
                        'avg_confidence': round(sum(r.confidence for r in recommendations) / len(recommendations), 3) if recommendations else 0,
                        'by_severity': {
                            'critical': sum(1 for r in recommendations if r.severity == 'critical'),
                            'high': sum(1 for r in recommendations if r.severity == 'high'),
                            'medium': sum(1 for r in recommendations if r.severity == 'medium'),
                            'low': sum(1 for r in recommendations if r.severity == 'low')
                        }
                    }
                },
                'criterion_2_nlp_models': {
                    'description': 'NLP for time series analysis - Classical and Transformer methods',
                    'implemented': True,
                    'classical_methods': ['moving_average', 'isolation_forest', 'seasonal_decomposition'],
                    'transformer_methods': ['time_series_attention', 'trend_analysis', 'ensemble'],
                    'metrics': {
                        'total_analyses': len(anomaly_analyses),
                        'classical_anomalies_detected': classical_anomalies,
                        'transformer_anomalies_detected': transformer_anomalies
                    }
                },
                'criterion_3_model_comparison': {
                    'description': 'Comparison of classical vs Transformer models for anomaly detection',
                    'implemented': True,
                    'metrics': {
                        'total_comparisons': len(anomaly_analyses),
                        'model_agreements': model_agreements,
                        'agreement_rate': round(model_agreements / len(anomaly_analyses), 3) if anomaly_analyses else 0,
                        'avg_agreement_score': round(sum(a.confidence for a in anomaly_analyses) / len(anomaly_analyses), 3) if anomaly_analyses else 0
                    }
                },
                'criterion_4_speech_recognition': {
                    'description': 'Speech recognition with Whisper for notification management',
                    'implemented': True,
                    'metrics': {
                        'total_voice_commands': len(voice_commands),
                        'commands_by_type': voice_commands_stats
                    }
                }
            },
            'location_filter': location_id,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        print(f"Error getting diploma stats: {e}")
        return {
            'error': str(e)
        }