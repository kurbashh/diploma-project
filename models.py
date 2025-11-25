from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# --- 1. ПОЛЬЗОВАТЕЛИ И ЛОГИ (Скрин 2) ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)       # admin, engineer, product
    is_online = Column(Boolean, default=False)
    hashed_password = Column(String, nullable=False)

    logs = relationship("ActionLog", back_populates="user")


class ActionLog(Base):
    """История действий"""
    __tablename__ = "action_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="logs")

# --- 2. ЛОКАЦИИ И ТИПЫ ДАТЧИКОВ ---

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    sensors = relationship("Sensor", back_populates="location")
    measurements = relationship("Measurement", back_populates="location")


class SensorType(Base):
    """Категория: Температура, Влажность"""
    __tablename__ = "sensor_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True) # Temperature
    unit = Column(String)              # °C

    sensors = relationship("Sensor", back_populates="sensor_type")

# --- 3. ДАТЧИКИ И ИЗМЕРЕНИЯ (Скрины 1 и 4) ---

class Sensor(Base):
    """
    Физическое устройство.
    Хранит настройки (слайдеры, кнопки).
    """
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    
    location_id = Column(Integer, ForeignKey("locations.id"))
    sensor_type_id = Column(Integer, ForeignKey("sensor_types.id"))

    # Настройки управления (Скрин "Датчики")
    is_active = Column(Boolean, default=True)   # Тоггл
    target_value = Column(Float, nullable=True) # Слайдер

    location = relationship("Location", back_populates="sensors")
    sensor_type = relationship("SensorType", back_populates="sensors")
    measurements = relationship("Measurement", back_populates="sensor")


class Measurement(Base):
    """История данных для графиков"""
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, index=True)
    
    sensor_id = Column(Integer, ForeignKey("sensors.id"))
    location_id = Column(Integer, ForeignKey("locations.id")) # Дублируем для удобства фильтрации
    
    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    sensor = relationship("Sensor", back_populates="measurements")
    location = relationship("Location", back_populates="measurements")

# --- 4. УВЕДОМЛЕНИЯ (Скрин 1) ---

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- 5. ОТЧЕТЫ (Скрин 3) ---

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow)