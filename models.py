from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    metrics = relationship("MetricValue", back_populates="location")


class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    light = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    values = relationship("MetricValue", back_populates="metric")  # <- добавлено


class MetricValue(Base):
    __tablename__ = "metric_values"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer, ForeignKey("metrics.id"))
    location_id = Column(Integer, ForeignKey("locations.id"))

    value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    metric = relationship("Metric", back_populates="values")
    location = relationship("Location", back_populates="metrics")