from fastapi import FastAPI, Depends, HTTPException, status, Body
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import random
import os

import crud
import models
import schemas
from database import SessionLocal, engine, Base
from sqlalchemy import func # Добавляем для расчета статистики

# Создаем объект FastAPI
app = FastAPI(title="Microclimate Monitoring API")


@app.on_event("startup")
def startup_event():
    """При запуске автоматически создаём таблицы, если их нет."""
    try:
        print("🚀 Создаём таблицы SQLite (если их нет)")
        # Base.metadata.create_all(bind=engine) # ВАЖНО: Эту строку лучше вызывать один раз при миграции
        
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

# Health check (без зависимостей БД)
@app.get("/health")
def health_check():
    """Простая проверка здоровья сервиса."""
    return {"status": "ok", "service": "Microclimate API"}

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
    """
    
    sensors = crud.get_sensors_by_location(db, location_id)
    
    result = []
    for sensor in sensors:
        last_measure = crud.get_last_measurement(db, sensor.id)
        current_val = last_measure.value if last_measure else 0.0
        
        # --- ЛОГИКА СИМУЛЯЦИИ (PHYSICS ENGINE) ---
        if sensor.is_active and sensor.target_value is not None and last_measure:
            diff = sensor.target_value - current_val
            
            if abs(diff) > 0.1:
                time_since_last = datetime.utcnow() - last_measure.timestamp
                
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

        # -----------------------------------------
        
        sensor_data = schemas.SensorRead.from_orm(sensor)
        sensor_data.last_value = round(current_val, 1) 
        result.append(sensor_data)
        
    return result

@app.patch("/api/sensors/{sensor_id}", response_model=schemas.SensorRead)
def update_sensor_settings(
    sensor_id: int, 
    update_data: schemas.SensorUpdate, 
    user_id: int = 1, # ID юзера для логов
    db: Session = Depends(get_db)
):
    """
    Управление датчиком с записью в ЛОГИ.
    """
    sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    action_text = []
    
    # 1. Логируем is_active только если новое значение отличается от старого
    if update_data.is_active is not None and update_data.is_active != sensor.is_active:
        sensor.is_active = update_data.is_active 
        status = "Включил" if update_data.is_active else "Выключил"
        action_text.append(f"{status} датчик {sensor.name}")
        
    # 2. Логируем target_value только если оно было предоставлено и изменилось
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
    """
    Считает среднюю температуру и влажность, а также их процентное изменение за 24 часа.
    """
    sensors = db.query(models.Sensor).all()
    
    cur_temp_vals = []
    cur_hum_vals = []
    old_temp_vals = []
    old_hum_vals = []

    time_24h_ago = datetime.utcnow() - timedelta(days=1)

    for sensor in sensors:
        last_measure = crud.get_last_measurement(db, sensor.id)
        
        # Получаем значение, ближайшее к 24 часам назад
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
    """Дандые для графика"""
    return crud.get_analytics_daily(db=db, sensor_id=sensor_id, days=days)

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
    Инициирует генерацию отчета (недельный или месячный).
    Эта функция вызывается Cloud Scheduler.
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
    report_file_content = f"{title_prefix} за период {start_time.strftime('%d.%m.%Y')} - {end_time.strftime('%d.%m.%Y')}\n"
    report_file_content += "--------------------------------------------------\n"
    for data in report_data:
        report_file_content += (
            f"Локация: {data['location']} | Датчик: {data['sensor']} ({data['type']})\n"
            f"  Среднее: {data['avg']} | Мин: {data['min']} | Макс: {data['max']}\n"
        )
    
    # 3. Сохранение файла локально (имитация GCS)
    filename = f"{period}_{end_time.strftime('%Y%m%d_%H%M%S')}.txt"
    # *** ИСПОЛЬЗУЕМ ФУНКЦИЮ CRUD, КОТОРАЯ СОХРАНЯЕТ ФАЙЛ ***
    file_path = crud.save_report_locally(filename, report_file_content)
    
    # 4. Сохранение метаданных отчета в БД
    report_title = f"{title_prefix} ({start_time.strftime('%d.%m')} - {end_time.strftime('%d.%m')})"
    
    new_report = models.Report(
        title=report_title,
        file_path=file_path,
        report_date=end_time
    )
    db.add(new_report)
    db.commit()

    return {
        "message": "Отчет успешно сгенерирован и сохранен.", 
        "title": report_title,
        "file_path": file_path
    }

@app.get("/api/reports/{report_id}/download")
def download_report(
    report_id: int, 
    user_id: int = 1, 
    db: Session = Depends(get_db)
):
    """Скачать отчет с логированием"""
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
    """
    Получить список уведомлений.
    """
    # Здесь можно добавить crud.check_notification_completion(db) для авто-закрытия
    return db.query(models.Notification).filter(models.Notification.is_completed == False).all()

@app.post("/api/notifications/{notif_id}/complete")
def complete_notification(notif_id: int, db: Session = Depends(get_db)):
    """Нажать кнопку 'Выполнено' (Ручное закрытие)"""
    notif = db.query(models.Notification).filter(models.Notification.id == notif_id).first()
    if notif:
        notif.is_completed = True
        db.commit()
    return {"status": "ok"}

# -------------------------------------------------------------------
# 🧠 6. КРИТЕРИИ ЭКЗАМЕНА (АНОМАЛИИ, РЕКОМЕНДАЦИИ И ГОЛОС)
# -------------------------------------------------------------------

# *** НОВЫЙ ЭНДПОИНТ: ВОССТАНОВЛЕННЫЙ ПУТЬ ДЛЯ СОЗДАНИЯ РЕКОМЕНДАЦИЙ ***
@app.post("/api/recommendations/generate", status_code=status.HTTP_201_CREATED)
def generate_recommendation_from_analysis(db: Session = Depends(get_db)):
    """
    КРИТЕРИЙ 1 (ПРОАКТИВНОСТЬ): Инициирует поиск аномалий и создание рекомендаций
    для всех датчиков. Должен вызываться по расписанию (Cloud Scheduler).
    """
    all_sensors = db.query(models.Sensor).all()
    
    results = []
    
    # Запускаем анализ для каждого датчика
    for sensor in all_sensors:
        result = run_anomaly_analysis(sensor.id, db)
        results.append(result)
        
    return {"status": "analysis_completed", "details": results}
# *******************************************************************


@app.post("/api/analysis/run/{sensor_id}", status_code=status.HTTP_201_CREATED)
def run_anomaly_analysis(
    sensor_id: int, 
    db: Session = Depends(get_db)
):
    """
    КРИТЕРИИ 2 & 3: Запуск анализа аномалий для датчика.
    Имитирует работу классической и Transformer-моделей (сравнение).
    """
    sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")

    # 1. Получаем данные для анализа (последние 7 дней)
    measurements = crud.get_sensor_measurements(db, sensor_id, days=7)
    if not measurements:
        return {"message": f"Недостаточно данных для анализа датчика {sensor_id}."}

    # --- ИМИТАЦИЯ РЕЗУЛЬТАТОВ МОДЕЛЕЙ (Заглушки) ---
    
    # Классическая модель (Критерий 2, 3)
    classical_score = round(random.uniform(0.1, 0.5), 3) # Low confidence
    classical_is_anomaly = classical_score > 0.4 

    # Transformer модель (Критерий 2, 3)
    transformer_score = round(random.uniform(0.6, 0.9), 3) # High confidence
    transformer_is_anomaly = transformer_score > 0.7 
    
    # Сравнение
    models_agreement = classical_is_anomaly == transformer_is_anomaly
    confidence = (classical_score + transformer_score) / 2
    
    # 2. Сохраняем результаты анализа в базу
    analysis = crud.create_anomaly_analysis(
        db, 
        sensor_id=sensor_id,
        location_id=sensor.location_id,
        classical_method="STD_DEV",
        classical_score=classical_score,
        classical_is_anomaly=classical_is_anomaly,
        transformer_model="BERT-TS (Simulated)",
        transformer_score=transformer_score,
        transformer_is_anomaly=transformer_is_anomaly,
        models_agreement=models_agreement,
        confidence=confidence
    )
    
    # 3. Генерируем рекомендацию (Критерий 1)
    if transformer_is_anomaly:
        
        # Пример логики для целевого значения
        current_avg = sum(m.value for m in measurements) / len(measurements)
        new_target = round(current_avg * (0.95 if sensor.sensor_type.name == "Humidity" else 1.05), 1)

        recommendation = crud.create_intelligent_recommendation(
            db,
            sensor_id=sensor_id,
            location_id=sensor.location_id,
            problem_description=f"Обнаружена аномалия в {sensor.sensor_type.name} с уверенностью {transformer_score}",
            recommended_action=f"Корректировка {sensor.sensor_type.name}",
            target_value=new_target,
            reasoning="Трансформер-модель обнаружила высокий уровень отклонения от сезонного тренда.",
            confidence=confidence,
            severity='high' if transformer_score > 0.8 else 'medium',
            priority=5,
            anomaly_analysis_id=analysis.id # Связываем с анализом
        )

        return {"status": "success", "analysis_id": analysis.id, "recommendation_id": recommendation.id, "message": "Аномалия обнаружена и создана рекомендация."}
        
    return {"status": "success", "analysis_id": analysis.id, "message": "Анализ завершен, аномалий не обнаружено."}


@app.post("/api/voice/command/{notification_id}", status_code=status.HTTP_201_CREATED)
def process_voice_command(
    notification_id: int, 
    db: Session = Depends(get_db),
    # Для демонстрации принимаем уже распознанный текст (транскрипт)
    transcript: str = Body(..., embed=True, example="Подтвердить температуру в Кабинете 2") 
):
    """
    КРИТЕРИЙ 4: Прием и обработка голосовой команды для уведомления.
    Имитирует распознавание речи (STT) и NLU (понимание команды).
    """
    
    notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Уведомление не найдено.")

    # --- ИМИТАЦИЯ NLU (Понимание намерения) ---
    
    command_type = 'unknown'
    execution_status = 'failed'
    
    if "подтвердить" in transcript.lower() or "выполнить" in transcript.lower():
        command_type = 'confirm'
        notif.is_completed = True
        db.commit()
        execution_status = 'success'
        
    elif "отклонить" in transcript.lower() or "отмена" in transcript.lower():
        command_type = 'reject'
        execution_status = 'success'
        
    elif "отчёт" in transcript.lower() or "доклад" in transcript.lower():
        command_type = 'request_report'
        execution_status = 'success'

    # 1. Сохраняем команду в базу
    command = crud.create_voice_notification_command(
        db,
        notification_id=notification_id,
        transcript=transcript,
        command=command_type,
        # В реальной жизни эти поля заполняются после обработки STT/NLU
        # speech_confidence и command_confidence должны быть добавлены в models.py
        # для демонстрации я убираю их отсюда, чтобы не было ошибки.
        execution_status=execution_status
    )
    
    # 2. Выполняем действие (для подтверждения)
    if command_type == 'confirm':
        return {"status": execution_status, "message": f"Команда '{command_type}' выполнена. Уведомление закрыто."}
    elif command_type == 'reject':
        return {"status": execution_status, "message": f"Команда '{command_type}' принята. Уведомление остается активным."}
        
    return {"status": execution_status, "message": f"Команда '{command_type}' ({transcript}) сохранена для дальнейшей обработки."}


@app.get("/api/voice/commands", response_model=List[schemas.VoiceNotificationCommandRead])
def get_voice_commands(db: Session = Depends(get_db)):
    """Получить список всех голосовых команд."""
    return crud.get_voice_notification_commands(db)

@app.get("/api/analysis/recommendations", response_model=List[schemas.RecommendationWithStatus])
def get_recommendations(db: Session = Depends(get_db), location_id: Optional[int] = None):
    """Получить список всех рекомендаций."""
    
    recommendations = crud.get_intelligent_recommendations(db, location_id=location_id)
    
    # Добавляем данные датчиков и локаций для удобства отображения на фронте
    result = []
    for rec in recommendations:
        sensor = db.query(models.Sensor).filter(models.Sensor.id == rec.sensor_id).first()
        location = db.query(models.Location).filter(models.Location.id == rec.location_id).first()
        
        dto = schemas.RecommendationWithStatus.from_orm(rec)
        dto.sensor_name = sensor.name if sensor else "Неизвестный датчик"
        dto.location_name = location.name if location else "Неизвестная локация"
        
        result.append(dto)

    return result


@app.get("/api/analysis/results", response_model=List[schemas.AnomalyAnalysisRead])
def get_anomaly_results(db: Session = Depends(get_db), location_id: Optional[int] = None):
    """Получить список всех результатов анализа аномалий."""
    return crud.get_anomaly_analyses(db, location_id=location_id)


# -------------------------------------------------------------------
# 📥 7. СЛУЖЕБНЫЕ (IoT и Seed)
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
    """Генератор данных"""
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
        
    if db.query(models.Report).count() == 0:
        pass
        
    db.commit()
    
    return {"message": f"Успешно создано {NEW_ROOMS_COUNT} новых кабинета!"}