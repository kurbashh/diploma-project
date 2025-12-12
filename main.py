from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random

# Импортируем наши модули
import crud
import models
import schemas
from database import SessionLocal, engine, Base, FORCE_SQLITE
# Внимание: для реальной работы с GCS вам понадобится установить 
# библиотеку google-cloud-storage и добавить ее импорт в crud.py
# Здесь используется заглушка, которая возвращает фиктивный URL GCS.

# Создаем объект FastAPI
app = FastAPI(title="Microclimate Monitoring API")


@app.on_event("startup")
def startup_event():
    """При локальном запуске с SQLite — автоматически создаём таблицы, если их нет.

    Это полезно для разработки: не требуется запускать Alembic/миграции.
    Чтобы включить поведение, установите `FORCE_SQLITE=1` в окружении.
    """
    try:
        if FORCE_SQLITE:
            print("FORCE_SQLITE=1 — создаём таблицы SQLite (если их нет)")
            Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"Warning: failed to create tables on startup: {e}")

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
        # Если датчик включен и есть разница между целью и фактом
        if sensor.is_active and sensor.target_value is not None:
            diff = sensor.target_value - current_val
            
            # Если разница существенная (больше 0.1)
            if abs(diff) > 0.1:
                # Проверяем, давно ли было последнее обновление (чтобы не спамить базу при частом обновлении)
                # Обновляем "физику" не чаще чем раз в 5 секунд
                time_since_last = datetime.utcnow() - last_measure.timestamp if last_measure else timedelta(seconds=100)
                
                if time_since_last.total_seconds() > 5:
                    # Двигаемся к цели на 10% от оставшегося пути (эффект плавного замедления)
                    step = diff * 0.1
                    
                    # Но не меньше 0.1 градуса за раз, чтобы не застрять
                    if abs(step) < 0.1:
                        step = 0.1 if diff > 0 else -0.1
                        
                    # Добавляем немного шума (случайности), чтобы выглядело как реальный датчик
                    noise = random.uniform(-0.05, 0.05)
                    new_val = current_val + step + noise
                    
                    # Создаем запись в базе (будто датчик прислал данные)
                    new_measure = models.Measurement(
                        sensor_id=sensor.id,
                        location_id=sensor.location_id,
                        value=round(new_val, 2),
                        timestamp=datetime.utcnow()
                    )
                    db.add(new_measure)
                    db.commit()
                    
                    # Обновляем значение для выдачи на фронт
                    current_val = new_val

        # -----------------------------------------
        
        # Создаем экземпляр Pydantic
        sensor_data = schemas.SensorRead.from_orm(sensor)
        sensor_data.last_value = round(current_val, 1) # Округляем для красоты
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
    
    # ЛОГИКА ЛОГИРОВАНИЯ: Сравниваем новое значение с текущим в БД, чтобы не спамить лог.
    
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
        # Сохраняем изменения в таблице sensors
        db.commit()
        db.refresh(sensor)
        
        # Записываем в action_logs
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
        
        old_measure = db.query(models.Measurement)\
            .filter(models.Measurement.sensor_id == sensor.id, 
                    models.Measurement.timestamp <= time_24h_ago)\
            .order_by(models.Measurement.timestamp.desc())\
            .first()
        
        if last_measure:
            # Используем sensor_type.name для определения типа
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
    Инициирует генерацию отчета (недельный или месячный).
    Эта функция будет вызываться Cloud Scheduler.
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

    # 2. Формирование содержания отчета (имитация)
    report_content_lines = [f"{title_prefix} за период {start_time.strftime('%d.%m.%Y')} - {end_time.strftime('%d.%m.%Y')}\n"]
    report_content_lines.append("--------------------------------------------------")
    for data in report_data:
        report_content_lines.append(
            f"Локация: {data['location']} | Датчик: {data['sensor']} ({data['type']})\n"
            f"  Среднее: {data['avg']} | Мин: {data['min']} | Макс: {data['max']}"
        )
    report_file_content = "\n".join(report_content_lines)
    
    # 3. Загрузка файла в GCS и получение URL
    
    # Полный путь в бакете
    blob_path = f"reports/{period}_{end_time.strftime('%Y%m%d')}.txt"
    bucket_name = 'reports-backet' # Ваш бакет

    # Вызываем функцию CRUD для загрузки
    file_url = crud.upload_to_gcs(
        bucket_name=bucket_name,
        file_path=blob_path,
        content=report_file_content,
        content_type='text/plain' # В реальной жизни было бы application/pdf
    )
    
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
        # В этом блоке мы не создаем отчеты, чтобы они не мешали автоматической генерации
        pass
        
    db.commit()
    
    return {"message": f"Успешно создано {NEW_ROOMS_COUNT} новых кабинета!"}