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
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=True) # Добавлено
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=True)    # Добавлено
    required_target_value = Column(Float, nullable=True)

    location = relationship("Location")

# --- 5. ОТЧЕТЫ (Скрин 3) ---

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    report_date = Column(DateTime, default=datetime.utcnow)


# --- 6. АНАЛИЗ АНОМАЛИЙ (Для интеллектуальной диагностики) ---

class AnomalyAnalysis(Base):
    """
    Результаты анализа аномалий в данных датчиков.
    Использует классические и Transformer методы для выделения аномалий.
    """
    __tablename__ = "anomaly_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    
    # Данные для анализа
    analysis_period_start = Column(DateTime)  # Начало периода анализа
    analysis_period_end = Column(DateTime)    # Конец периода анализа
    
    # Результаты классического анализа (статистический)
    classical_method = Column(String)  # Метод (moving_average, std_dev, seasonal_decompose)
    classical_anomaly_score = Column(Float)  # Оценка аномалии 0-1
    classical_is_anomaly = Column(Boolean)  # Это ли аномалия?
    classical_description = Column(String)  # Описание аномалии
    
    # Результаты Transformer анализа (нейросетевой)
    transformer_model = Column(String)  # Название модели
    transformer_anomaly_score = Column(Float)  # Оценка аномалии 0-1
    transformer_is_anomaly = Column(Boolean)
    transformer_description = Column(String)
    
    # Метрики сравнения
    models_agreement = Column(Boolean)  # Согласны ли модели?
    confidence = Column(Float)  # Уверенность в результате
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sensor = relationship("Sensor")
    location = relationship("Location")


# --- 7. ИНТЕЛЛЕКТУАЛЬНЫЕ РЕКОМЕНДАЦИИ ---

class IntelligentRecommendation(Base):
    """
    Интеллектуальные рекомендации по коррекции микроклимата.
    Генерируются на основе анализа аномалий.
    """
    __tablename__ = "intelligent_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    anomaly_analysis_id = Column(Integer, ForeignKey("anomaly_analyses.id"), nullable=False)
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    
    # Рекомендация
    problem_description = Column(String)  # Описание проблемы
    recommended_action = Column(String)   # Рекомендуемое действие
    target_value = Column(Float)  # Целевое значение параметра
    
    # Обоснование
    reasoning = Column(String)  # Объяснение почему эта рекомендация
    confidence = Column(Float)  # Уверенность в рекомендации 0-1
    
    # Статус выполнения (интеграция с уведомлением)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=True)
    is_implemented = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    implemented_at = Column(DateTime, nullable=True)
    
    anomaly = relationship("AnomalyAnalysis")
    sensor = relationship("Sensor")
    location = relationship("Location")
    notification = relationship("Notification")


# --- 8. ГОЛОСОВЫЕ КОМАНДЫ (Для управления уведомлениями) ---

class VoiceNotificationCommand(Base):
    """
    История голосовых команд для подтверждения или отклонения уведомлений.
    """
    __tablename__ = "voice_notification_commands"
    
    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Распознанная речь
    transcript = Column(String, nullable=False)
    detected_language = Column(String, default='en')
    speech_confidence = Column(Float)
    
    # Интерпретированная команда
    command = Column(String)  # 'confirm', 'reject', 'modify', 'request_report'
    command_confidence = Column(Float)
    
    # Результат
    execution_status = Column(String, default='pending')  # 'success', 'failed'
    executed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    notification = relationship("Notification")
    user = relationship("User")