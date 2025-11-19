from pydantic import BaseModel
from datetime import datetime


class MetricBase(BaseModel):
    name: str
    unit: str


class MetricCreate(BaseModel):
    temperature: float
    humidity: float
    light: float


class Metric(MetricBase):
    id: int

    class Config:
        orm_mode = True


class MetricRead(MetricCreate):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True


class LocationBase(BaseModel):
    name: str


class LocationCreate(LocationBase):
    pass


class Location(LocationBase):
    id: int

    class Config:
        orm_mode = True


class MetricValueBase(BaseModel):
    value: float
    timestamp: datetime | None = None


class MetricValueCreate(MetricValueBase):
    metric_id: int
    location_id: int


class MetricValue(MetricValueBase):
    id: int
    metric: Metric
    location: Location

    class Config:
        orm_mode = True