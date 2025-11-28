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