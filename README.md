Microclimate — Local Run (SQLite)

Краткие инструкции для локальной разработки с использованием SQLite.

**Требования**
- Python 3.8+ (рекомендуется 3.11)
- Docker (опционально)

**1) Быстрая настройка (macOS, zsh)**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2) Запуск с локальной SQLite**
- Включите режим принудительного использования SQLite и запустите Uvicorn:
```bash
export FORCE_SQLITE=1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
- По умолчанию будет создан файл `sql_app.db` в корне проекта и таблицы (если их нет).
- Откройте Swagger UI: http://127.0.0.1:8000/docs

**3) Наполнение тестовыми данными**
- Если в проекте реализован эндпоинт `POST /api/seed_data`, вызовите его через Swagger или curl:
```bash
curl -X POST http://127.0.0.1:8000/api/seed_data
```

**4) Запуск симулятора датчиков**
- По умолчанию `simulator.py` отправляет данные на `BASE_URL` внутри файла.
- Для локальной разработки откройте `simulator.py` и поменяйте:
```py
BASE_URL = "http://127.0.0.1:8000"
```
- Затем запустите:
```bash
python simulator.py
```

**5) Docker (опционально)**
- Собрать образ:
```bash
docker build -t microclimate .
```
- Запустить контейнер (используем SQLite внутри контейнера):
```bash
docker run -e FORCE_SQLITE=1 -e PORT=8000 -p 8000:8000 microclimate
```
- После старта контейнера Swagger будет доступен на `http://localhost:8000/docs`.

**6) Переключение на PostgreSQL / Cloud SQL**
- Для работы с реальной БД (Postgres/Cloud SQL) задайте переменные окружения `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME` (или `CLOUD_SQL_CONNECTION_NAME`), и не выставляйте `FORCE_SQLITE=1`.
- `alembic.ini` в проекте настроен на PostgreSQL — используйте Alembic для миграций в проде.

**Где хранятся файлы БД**
- Файл SQLite: `./sql_app.db` (в корне проекта).

Если хотите, могу также:
- добавить компактный `Makefile` или `scripts/run.sh` для команд выше;
- настроить Dockerfile чтобы по умолчанию выставлял `PORT=8000`.
