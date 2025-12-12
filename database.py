from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# --- ЛОКАЛЬНАЯ SQLite БАЗА ДАННЫХ ---

# Путь к файлу базы данных
DATABASE_FILE = os.environ.get("DATABASE_FILE", "./sql_app.db")

# URL подключения к SQLite
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

print(f"--- Connecting to local SQLite: {DATABASE_FILE} ---")

# Создание движка для SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Создает и закрывает сессию базы данных"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()