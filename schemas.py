from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- 1. БАЗОВЫЕ СХЕМЫ (Users, Logs) ---

class UserBase(BaseModel):
    full_name: str
    role: str
    is_online: bool = False

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    class Config:
        from_attributes = True

# [НОВОЕ] Специальная схема для списка сотрудников (UI)
class UserListDTO(BaseModel):
    id: str         # UI любит строки в ID
    name: str
    role: str
    status: str     # "Онлайн" вместо True/False
    # icon определим на фронте
    
    class Config:
        from_attributes = True

class ActionLogRead(BaseModel):
    id: int
    action: str
    timestamp: datetime
    user_name: Optional[str] = "System"
    class Config:
        from_attributes = True

# [НОВОЕ] Специальная схема для Истории действий (UI)
class ActionLogDTO(BaseModel):
    id: str
    user: str
    role: str
    action: str
    time: str       # Время "12:05:00" строкой
    
    class Config:
        from_attributes = True


# --- 2. ДАТЧИКИ И ТИПЫ (Sensors) ---

class SensorTypeRead(BaseModel):
    id: int
    name: str
    unit: str
    class Config:
        from_attributes = True

class SensorBase(BaseModel):
    name: str
    is_active: bool
    target_value: Optional[float] = None

class SensorUpdate(BaseModel):
    is_active: Optional[bool] = None
    target_value: Optional[float] = None

class SensorRead(SensorBase):
    id: int
    sensor_type: SensorTypeRead
    location_id: int # <--- ДОБАВЛЕНО/ПРОВЕРЕНО
    last_value: Optional[float] = 0.0 # Обязательно Optional

    class Config:
        from_attributes = True


# --- 3. ИЗМЕРЕНИЯ И ГРАФИКИ ---

class MeasurementBase(BaseModel):
    value: float

class MeasurementCreate(BaseModel):
    value: float
    sensor_id: int

class MeasurementRead(BaseModel):
    id: int
    value: float
    timestamp: datetime
    sensor_id: int
    class Config:
        from_attributes = True

# [НОВОЕ] Схема для Графика (LineChart)
# Бэкенд будет отдавать список таких объектов
class ChartPoint(BaseModel):
    label: str  # "22.11" или "12:00"
    value: float


# --- 4. УВЕДОМЛЕНИЯ И ОТЧЕТЫ ---

class NotificationRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    is_completed: bool
    created_at: datetime
    
    # [ИСПРАВЛЕНО] Добавили контекст, чтобы кнопка работала
    sensor_id: Optional[int] = None
    location_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class ReportRead(BaseModel):
    id: int
    title: str
    report_date: datetime
    file_path: str
    class Config:
        from_attributes = True

# --- 5. ЛОКАЦИИ (Для выпадающего списка) ---
class LocationRead(BaseModel):
    id: int
    name: str # Название кабинета/склада
    class Config:
        from_attributes = True


# --- 6. АНАЛИЗ АНОМАЛИЙ ---

class AnomalyAnalysisBase(BaseModel):
    sensor_id: int
    location_id: int
    classical_method: str
    classical_anomaly_score: float
    classical_is_anomaly: bool
    transformer_model: str
    transformer_anomaly_score: float
    transformer_is_anomaly: bool

class AnomalyAnalysisRead(AnomalyAnalysisBase):
    id: int
    models_agreement: bool
    confidence: float
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- 7. ИНТЕЛЛЕКТУАЛЬНЫЕ РЕКОМЕНДАЦИИ ---

class IntelligentRecommendationBase(BaseModel):
    sensor_id: int
    location_id: int
    problem_description: str
    recommended_action: str
    target_value: float
    reasoning: str
    confidence: float

class IntelligentRecommendationCreate(IntelligentRecommendationBase):
    anomaly_analysis_id: int

class IntelligentRecommendationRead(IntelligentRecommendationBase):
    id: int
    is_implemented: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class RecommendationWithStatus(IntelligentRecommendationRead):
    """DTO с полной информацией для фронтенда"""
    sensor_name: Optional[str] = None
    sensor_type: Optional[str] = None
    location_name: Optional[str] = None
    notification_id: Optional[int] = None


# --- 8. ГОЛОСОВЫЕ КОМАНДЫ ДЛЯ УВЕДОМЛЕНИЙ ---

class VoiceNotificationCommandBase(BaseModel):
    transcript: str
    detected_language: str = 'en'
    speech_confidence: float
    command: str
    command_confidence: float

class VoiceNotificationCommandCreate(VoiceNotificationCommandBase):
    notification_id: int
    user_id: Optional[int] = None

class VoiceNotificationCommandRead(VoiceNotificationCommandBase):
    id: int
    notification_id: int
    execution_status: str
    created_at: datetime
    executed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True