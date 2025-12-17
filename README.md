# 🎓 Microclimate Monitoring System - Diploma Project

**Дипломный проект:** Система проактивного мониторинга микроклимата с NLP-анализом аномалий датчиков и голосовым управлением.

---

## 🏆 4 Критерия Дипломной Работы (по 25% каждый)

### **КРИТЕРИЙ 1: Практическое решение проблемы** ✅
- **Задача:** Проактивное управление микроклиматом с интеллектуальными рекомендациями
- **Решение:** Система обнаруживает аномалии в данных датчиков и генерирует исполняемые рекомендации с целевыми значениями
- **Особенность:** Механизм автоверификации - система проверяет реализацию рекомендации по целевому значению
- **Файлы:**
  - `intelligent_recommendation_engine.py` (652 строк)
  - API endpoint: `POST /api/recommendations/generate`

### **КРИТЕРИЙ 2: Два и более NLP модели** ✅
- **Задача:** Применить разные подходы к анализу данных датчиков
- **Классические методы (3):**
  1. Moving Average Detector - скользящее окно со статистикой
  2. Isolation Forest - ML-based обнаружение выбросов
  3. Seasonal Decomposition - анализ циклических паттернов
- **Трансформер методы (3):**
  1. Time Series with Attention - внимание и реконструкция
  2. Trend Analysis - анализ направления и ускорения
  3. Ensemble Detector - комбинирует все методы
- **Файлы:**
  - `anomaly_detection_classical.py` (661 строк)
  - `anomaly_detection_transformer.py` (509 строк)
  - API endpoint: `GET /api/sensors/{sensor_id}/anomalies`

### **КРИТЕРИЙ 3: Сравнение классических и Трансформер моделей** ✅
- **Задача:** Сравнивать результаты разных подходов
- **Метрики:**
  - Согласие моделей (models_agreement)
  - Оценки аномалии (anomaly scores)
  - Уверенность в результате (confidence)
  - Консенсус решение (consensus anomaly detection)
- **База данных:** Таблица `AnomalyAnalysis` сохраняет все результаты
- **API endpoint:** `GET /api/diploma/analysis-stats`

### **КРИТЕРИЙ 4: Распознавание речи** ✅
- **Задача:** Голосовое управление уведомлениями
- **Технология:** Whisper от OpenAI для транскрибирования
- **Поддерживаемые команды:**
  - ✓ Confirm / Да - подтверждение рекомендации
  - ✓ Reject / Нет - отклонение рекомендации
  - ✓ Modify / Изменить - модификация целевого значения
  - ✓ Request Info - запрос информации об аномалии
  - ✓ Request Report - запрос исторического отчета
- **Многоязычность:** Русский и английский
- **Файлы:**
  - `voice_notification_commands.py` (450+ строк)
  - API endpoint: `POST /api/voice/notification-command`

---

## 📋 Требования
- Python 3.8+ (рекомендуется 3.11)
- CUDA (опционально, для ускорения Transformer моделей)

## 🚀 Быстрый старт

### 1. Установка зависимостей

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Запуск сервера

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

При первом запуске автоматически создастся:
- ✅ База данных `sql_app.db`
- ✅ Все необходимые таблицы (включая новые для анализа)
- ✅ Папка `reports/` для отчётов

**Swagger UI доступен:** http://127.0.0.1:8000/docs

### 3. Наполнение тестовыми данными

Через Swagger UI или curl:
```bash
curl -X POST http://127.0.0.1:8000/api/seed_data
```

Это создаст:
- 3 кабинета разных типов (server_room, data_center, office)
- Температурные и влажностные датчики
- 24 часа исторических данных для каждого датчика
- Тестового пользователя

### 4. Запуск симулятора датчиков

Откройте `simulator.py` и убедитесь, что URL правильный:
```python
BASE_URL = "http://127.0.0.1:8000"
```

Запустите симулятор:
```bash
python simulator.py
```

Симулятор будет каждые 30 секунд отправлять данные с датчиков.

---

## 🎓 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ API

### Анализ аномалий (CRITERION 2&3)

```bash
# Анализ датчика с использованием классических + Transformer методов
curl -X GET "http://127.0.0.1:8000/api/sensors/1/anomalies?days=7"

# Ответ:
{
  "sensor_id": 1,
  "sensor_name": "Server Room Temperature",
  "measurements_count": 168,
  "analysis": {
    "classical": {
      "is_anomaly": true,
      "score": 0.78,
      "description": "Temperature significantly above normal range",
      "method": "moving_average + isolation_forest + seasonal"
    },
    "transformer": {
      "is_anomaly": true,
      "score": 0.82,
      "reconstruction_error": 0.15,
      "trend_info": {"direction": "up", "acceleration": 0.05},
      "models_agree": true
    },
    "comparison": {
      "models_agree": true,
      "consensus_is_anomaly": true,
      "agreement_score": 0.95,
      "analysis_id": 123
    }
  }
}
```

### Генерация рекомендаций (CRITERION 1)

```bash
# Генерировать рекомендации для локации
curl -X POST "http://127.0.0.1:8000/api/recommendations/generate" \
  -H "Content-Type: application/json" \
  -d '{"location_id": 1, "only_anomalies": true}'

# Ответ:
{
  "location_id": 1,
  "location_name": "Server Room",
  "recommendations_count": 2,
  "recommendations": [
    {
      "sensor_name": "Temperature",
      "problem_description": "Temperature is 28.5°C, 3.5°C above normal range (18-25°C for server room)",
      "recommended_action": "Activate air conditioning or improve cooling system",
      "target_value": 22.0,
      "severity": "high",
      "priority": 5,
      "confidence": 0.92,
      "reasoning": "High temperature can damage server equipment. Estimated time to target: 15 minutes",
      "recommendation_id": 456
    },
    {
      "sensor_name": "Humidity",
      "problem_description": "Humidity is 82%, risk of condensation formation (dew point warnings)",
      "recommended_action": "Activate dehumidifier immediately, ensure air circulation",
      "target_value": 45.0,
      "severity": "critical",
      "priority": 5,
      "confidence": 0.88,
      "reasoning": "Humidity above 80% creates condensation risk. Hardware protection critical",
      "recommendation_id": 457
    }
  ]
}
```

### Обработка голосовых команд (CRITERION 4)

```bash
# Отправить голосовую команду для управления уведомлением
curl -X POST "http://127.0.0.1:8000/api/voice/notification-command" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_file_path": "/path/to/command.wav",
    "notification_id": 1,
    "sensor_id": 1
  }'

# Ответ:
{
  "success": true,
  "command": "confirm",
  "confidence_speech": 0.98,
  "confidence_command": 0.95,
  "transcript": "да, согласен, реализуй это",
  "detected_language": "ru",
  "action_taken": "Recommendation confirmed, implementing changes",
  "voice_command_id": 789,
  "notification_id": 1
}
```

### Статистика дипломной работы (DIPLOMA STATS)

```bash
# Получить общую статистику по всем 4 критериям
curl -X GET "http://127.0.0.1:8000/api/diploma/analysis-stats?location_id=1"

# Ответ:
{
  "diploma_criteria": {
    "criterion_1_practical_problem": {
      "status": "✅ IMPLEMENTED",
      "description": "Proactive microclimate monitoring with intelligent recommendations",
      "metrics": {
        "total_recommendations": 42,
        "avg_confidence": 0.89,
        "by_severity": {
          "critical": 5,
          "high": 12,
          "medium": 18,
          "low": 7
        }
      }
    },
    "criterion_2_nlp_models": {
      "status": "✅ IMPLEMENTED",
      "description": "NLP for time series analysis - Classical and Transformer methods",
      "classical_methods": ["moving_average", "isolation_forest", "seasonal_decomposition"],
      "transformer_methods": ["time_series_attention", "trend_analysis", "ensemble"],
      "metrics": {
        "total_analyses": 156,
        "classical_anomalies_detected": 34,
        "transformer_anomalies_detected": 38
      }
    },
    "criterion_3_model_comparison": {
      "status": "✅ IMPLEMENTED",
      "description": "Comparison of classical vs Transformer models for anomaly detection",
      "metrics": {
        "total_comparisons": 156,
        "model_agreements": 142,
        "agreement_rate": 0.91,
        "avg_agreement_score": 0.87
      }
    },
    "criterion_4_speech_recognition": {
      "status": "✅ IMPLEMENTED",
      "description": "Speech recognition with Whisper for notification management",
      "metrics": {
        "total_voice_commands": 28,
        "commands_by_type": {
          "confirm": 12,
          "reject": 5,
          "modify": 6,
          "request_info": 3,
          "request_report": 2,
          "unknown": 0
        }
      }
    }
  }
}
```

---

## 📁 Структура проекта

```
diploma-project/
├── main.py                              # FastAPI приложение (759 строк)
├── database.py                          # SQLite подключение
├── models.py                            # SQLAlchemy модели
├── schemas.py                           # Pydantic схемы
├── crud.py                              # CRUD функции (450+ строк)
│
├── anomaly_detection_classical.py       # CRITERION 2: Классические методы (661 строк)
├── anomaly_detection_transformer.py     # CRITERION 2: Трансформер методы (509 строк)
├── intelligent_recommendation_engine.py # CRITERION 1: Рекомендации (652 строк)
├── voice_notification_commands.py       # CRITERION 4: Голосовые команды (450+ строк)
│
├── diploma_analysis.ipynb               # Jupyter notebook с примерами
├── simulator.py                         # Симулятор IoT датчиков
├── speech_recognition.py                # Legacy модуль распознавания речи
│
├── requirements.txt                     # Python зависимости
├── sql_app.db                          # База данных (создаётся автоматически)
└── reports/                            # Папка с отчётами (создаётся автоматически)
```

---

## 🔌 КЛЮЧЕВЫЕ НОВЫЕ API ЭНДПОИНТЫ

### Анализ аномалий (CRITERION 2&3)
```
GET /api/sensors/{sensor_id}/anomalies?days=7
```
Анализирует датчик с использованием 6 методов (3 классических + 3 трансформер), сравнивает результаты.

### Генерация рекомендаций (CRITERION 1)
```
POST /api/recommendations/generate
```
Генерирует исполняемые рекомендации с целевыми значениями на основе аномалий.

### Обработка голосовых команд (CRITERION 4)
```
POST /api/voice/notification-command
```
Распознаёт голосовые команды управления уведомлениями (Whisper + парсер команд).

### Статистика диплома
```
GET /api/diploma/analysis-stats?location_id={id}
```
Получает полную статистику по всем 4 критериям дипломной работы.

---

## 📊 Новые таблицы базы данных

### AnomalyAnalysis
Сохраняет результаты анализа аномалий для сравнения моделей:
```sql
- sensor_id (FK)
- location_id (FK)
- classical_method (String)
- classical_anomaly_score (Float 0-1)
- classical_is_anomaly (Boolean)
- transformer_model (String)
- transformer_anomaly_score (Float 0-1)
- transformer_is_anomaly (Boolean)
- models_agreement (Boolean)  -- согласие моделей
- confidence (Float 0-1)
- analysis_timestamp
```

### IntelligentRecommendation
Хранит сгенерированные рекомендации:
```sql
- sensor_id (FK)
- location_id (FK)
- problem_description (Text)
- recommended_action (Text)
- target_value (Float)  -- CRITICAL для автоверификации!
- reasoning (Text)
- confidence (Float 0-1)
- severity (Enum: low, medium, high, critical)
- priority (Integer 1-5)
- created_at
```

### VoiceNotificationCommand
История голосовых команд:
```sql
- notification_id (FK)
- transcript (String)
- command (String: confirm, reject, modify, request_info, request_report, unknown)
- execution_status (String)
- execution_timestamp
```

---

## 🧹 Очистка данных

Удалите файл базы данных:
```bash
rm sql_app.db
```

При следующем запуске создастся новая пустая база.

---

## ❓ Проблемы и решения

**Ошибка при импорте transformers:**
```bash
pip install transformers torch scikit-learn
```

**Ошибка при загрузке Whisper:**
```bash
pip install openai-whisper librosa
```

**Модели не загружаются:**
- Проверьте интернет соединение (первая загрузка скачивает модели)
- Модели кэшируются в `~/.cache/huggingface/`
- Для Transformer требуется 2+ GB свободной памяти

**База данных не создаётся:**
- Проверьте права на запись в текущей директории
- Убедитесь, что установлен SQLAlchemy

**Симулятор не отправляет данные:**
- Проверьте, что сервер запущен на `http://127.0.0.1:8000`
- Убедитесь, что выполнили `/api/seed_data` для создания датчиков

**Голосовые команды не работают:**
- Установите Whisper: `pip install openai-whisper librosa`
- Убедитесь, что audio_file_path указан правильно
- Проверьте формат файла (поддерживаются: mp3, wav, m4a, flac)

---

## 📝 Лицензия

Дипломный проект - Система проактивного мониторинга микроклимата
