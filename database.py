from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# --- 1. Параметры подключения ---

# Читаем переменные окружения
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")

# Эти две переменные определяют тип подключения
CLOUD_SQL_CONNECTION_NAME = os.environ.get("CLOUD_SQL_CONNECTION_NAME")
DB_HOST = os.environ.get("DB_HOST") # <--- НОВАЯ ПЕРЕМЕННАЯ (IP адрес)

# Если нужно принудительно использовать локальную SQLite (удобно для разработки),
# установите переменную окружения `FORCE_SQLITE=1`.
FORCE_SQLITE = os.environ.get("FORCE_SQLITE", "0") == "1"

# Формируем URL подключения
SQLALCHEMY_DATABASE_URL = ""
if FORCE_SQLITE:
    # Принудительное подключение к локальной SQLite (DEV)
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    print("--- FORCE_SQLITE=1 -> Connecting to local SQLite ---")

elif DB_HOST:
    # --- ВАРИАНТ 1: Подключение по Private IP (через VPC) ---
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/{DB_NAME}"
    )
    print(f"--- Connecting to Cloud SQL via Private IP ({DB_HOST}) ---")

elif CLOUD_SQL_CONNECTION_NAME:
    # --- ВАРИАНТ 2: Подключение через Unix Socket ---
    SQLALCHEMY_DATABASE_URL = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}?host=/cloudsql/{CLOUD_SQL_CONNECTION_NAME}"
    )
    print("--- Connecting to Cloud SQL via Unix Socket ---")

else:
    # --- ВАРИАНТ 3: Локальная разработка (SQLite) ---
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    print("--- Connecting to local SQLite ---")


# Создание движка
if not FORCE_SQLITE and (DB_HOST or CLOUD_SQL_CONNECTION_NAME):
    # Для PostgreSQL
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
else:
    # Для SQLite (по умолчанию или если FORCE_SQLITE=1)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()