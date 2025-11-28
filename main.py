from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random

# Импортируем наши модули
import crud
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

# -------------------------------------------------------------------
# 📍 1. ЛОКАЦИИ И ДАТЧИКИ
# -------------------------------------------------------------------

@app.get("/api/locations", response_model=List[schemas.LocationRead])
def get_locations(db: Session = Depends(get_db)):
    """Получить список всех локаций (кабинетов) для выпадающего списка."""
    return crud.get_all_locations(db)

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

@app.patch("/api/sensors/{sensor_id}", response_model=schemas.SensorRead)
def update_sensor_settings(
    sensor_id: int, 
    update_data: schemas.SensorUpdate, 
    user_id: int = 1, # ID юзера для логов (по умолчанию 1)
    db: Session = Depends(get_db)
):
    """
    Управление датчиком с записью в ЛОГИ.
    """
    sensor = db.query(models.Sensor).filter(models.Sensor.id == sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
    
    # 1. Формируем текст действия для логов
    action_text = []
    if update_data.is_active is not None:
        sensor.is_active = update_data.is_active
        status = "Включил" if update_data.is_active else "Выключил"
        action_text.append(f"{status} датчик {sensor.name}")
        
    if update_data.target_value is not None:
        sensor.target_value = update_data.target_value
        action_text.append(f"Изменил {sensor.name} на {update_data.target_value}")

    # 2. Если были изменения, пишем их в базу и в ЛОГИ
    if action_text:
        db.commit()
        db.refresh(sensor)
        
        # --- ЗАПИСЬ В ЖУРНАЛ ---
        full_action_description = ", ".join(action_text)
        new_log = models.ActionLog(
            user_id=user_id,
            action=full_action_description,
            timestamp=datetime.utcnow()
        )
        db.add(new_log)
        db.commit()

    # 3. Возвращаем обновленный датчик
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
    Считает среднюю температуру и влажность, а также % изменения за 24 часа.
    """
    sensors = db.query(models.Sensor).all()
    
    # Списки для текущих значений
    cur_temp_vals = []
    cur_hum_vals = []
    
    # Списки для значений 24 часа назад (для расчета изменения)
    old_temp_vals = []
    old_hum_vals = []

    time_24h_ago = datetime.utcnow() - timedelta(days=1)

    for sensor in sensors:
        # 1. Текущее значение (последнее доступное)
        last_measure = db.query(models.Measurement)\
            .filter(models.Measurement.sensor_id == sensor.id)\
            .order_by(models.Measurement.timestamp.desc())\
            .first()
        
        # 2. Старое значение (ближайшее к моменту "24 часа назад")
        # Ищем запись, которая была сделана ДО time_24h_ago, берем последнюю из них
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
    
    # Вспомогательные функции
    def get_avg(values):
        return sum(values) / len(values) if values else 0.0
        
    def get_percent_change(current, old):
        if not old or old == 0: return 0.0
        return ((current - old) / old) * 100

    # Считаем средние
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
    """Данные для графика (LineChart)"""
    stats = crud.get_analytics_daily(db=db, sensor_id=sensor_id, days=days)
    if not stats:
        return []
    return stats

@app.get("/api/history", response_model=List[schemas.MeasurementRead])
def get_history(sensor_id: int = None, db: Session = Depends(get_db)):
    """Сырые данные (последние 100 записей)"""
    query = db.query(models.Measurement)
    if sensor_id:
        query = query.filter(models.Measurement.sensor_id == sensor_id)
    return query.order_by(models.Measurement.timestamp.desc()).limit(100).all()

# -------------------------------------------------------------------
# 📄 3. ОТЧЕТЫ (ВОТ ОНИ!)
# -------------------------------------------------------------------

@app.get("/api/reports", response_model=List[schemas.ReportRead])
def get_reports(db: Session = Depends(get_db)):
    """Получить список доступных отчетов"""
    return db.query(models.Report).order_by(models.Report.report_date.desc()).all()

@app.get("/api/reports/{report_id}/download")
def download_report(
    report_id: int, 
    user_id: int = 1, 
    db: Session = Depends(get_db)
):
    """Скачать отчет с записью в логи"""
    report = db.query(models.Report).filter(models.Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Логируем скачивание
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
    """Возвращает список пользователей, отформатированный для UI"""
    return crud.get_users_for_ui(db)

@app.get("/api/logs", response_model=List[schemas.ActionLogDTO])
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    """История действий, отформатированная для UI"""
    return crud.get_logs_for_ui(db, limit=limit)

# -------------------------------------------------------------------
# 🔔 5. УВЕДОМЛЕНИЯ
# -------------------------------------------------------------------

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

# -------------------------------------------------------------------
# 📥 6. СЛУЖЕБНЫЕ (IoT и Seed)
# -------------------------------------------------------------------

@app.post("/api/measurements", status_code=status.HTTP_201_CREATED)
def record_measurement(
    measurement: schemas.MeasurementCreate, 
    db: Session = Depends(get_db)
):
    """Принимает новое измерение от скрипта-имитатора"""
    sensor = db.query(models.Sensor).filter(models.Sensor.id == measurement.sensor_id).first()
    if not sensor:
        raise HTTPException(status_code=404, detail="Sensor not found")
        
    db_measurement = models.Measurement(
        sensor_id=measurement.sensor_id, 
        location_id=sensor.location_id,
        value=measurement.value,
        timestamp=datetime.utcnow()
    )
    
    db.add(db_measurement)
    db.commit()
    return {"status": "recorded", "value": measurement.value}

@app.post("/api/seed_data")
def seed_database(db: Session = Depends(get_db)):
    """
    Генератор данных: При каждом вызове создает 3 НОВЫХ кабинета.
    """
    # 1. Типы
    t_temp = db.query(models.SensorType).filter(models.SensorType.name == "Temperature").first()
    if not t_temp:
        t_temp = models.SensorType(name="Temperature", unit="°C")
        db.add(t_temp)
    t_hum = db.query(models.SensorType).filter(models.SensorType.name == "Humidity").first()
    if not t_hum:
        t_hum = models.SensorType(name="Humidity", unit="%")
        db.add(t_hum)
    db.commit()

    # 2. Локации
    existing_count = db.query(models.Location).count()
    NEW_ROOMS_COUNT = 3

    for i in range(1, NEW_ROOMS_COUNT + 1):
        room_number = existing_count + i
        new_loc = models.Location(name=f"Кабинет {room_number}")
        db.add(new_loc)
        db.commit()
        db.refresh(new_loc)

        # 3. Датчики
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
        
        # 4. История
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

    # 5. Пользователь (инженер)
    if not db.query(models.User).filter(models.User.full_name == "Kseniya Kruchina").first():
        u1 = models.User(full_name="Kseniya Kruchina", role="engineer", is_online=True, hashed_password="xhz")
        db.add(u1)
        
    # 6. Тестовые Отчеты (Чтобы было что качать)
    if db.query(models.Report).count() == 0:
        r1 = models.Report(
            title="Недельный отчет (10.11 - 17.11)", 
            file_path="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            report_date=datetime.utcnow() - timedelta(days=2)
        )
        db.add(r1)

    db.commit()
    
    return {"message": f"Успешно создано {NEW_ROOMS_COUNT} новых кабинета (с {existing_count + 1})!"}