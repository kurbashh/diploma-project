from pydantic import BaseModel
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

class ActionLogRead(BaseModel):
    id: int
    action: str
    timestamp: datetime
    user_name: Optional[str] = "System"
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
    """Для изменения настроек (слайдеры, кнопки)"""
    is_active: Optional[bool] = None
    target_value: Optional[float] = None

class SensorRead(SensorBase):
    id: int
    sensor_type: SensorTypeRead
    last_value: float = 0.0  # Для отображения текущей цифры на карточке

    class Config:
        from_attributes = True

# --- 3. ИЗМЕРЕНИЯ (Measurements - то, чего не хватало) ---

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

# --- 4. УВЕДОМЛЕНИЯ И ОТЧЕТЫ ---

class NotificationRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    is_completed: bool
    created_at: datetime
    class Config:
        from_attributes = True

class ReportRead(BaseModel):
    id: int
    title: str
    report_date: datetime
    file_path: str
    class Config:
        from_attributes = True