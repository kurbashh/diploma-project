import requests
import time
import random
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/measurements"
INTERVAL_SECONDS = 30 

# ID ДАТЧИКОВ (должны совпадать с теми, что вы создали через /api/seed_data)
# Если вы запустили /api/seed_data, то:
# SENSOR_TEMP_ID = 1 (Температура)
# SENSOR_HUM_ID = 2 (Влажность)
SENSOR_TEMP_ID = 1
SENSOR_HUM_ID = 2

# РЕАЛИСТИЧНЫЕ ДИАПАЗОНЫ ЗНАЧЕНИЙ
# Температура (20°C +/- 2°C)
TEMP_RANGE = (18.0, 22.0)
# Влажность (55% +/- 5%)
HUM_RANGE = (50.0, 60.0)
# --- КОНФИГУРАЦИЯ ---


def generate_and_send(sensor_id, value_range):
    """Генерирует случайное значение и отправляет его в API."""
    
    # 1. Генерация случайного значения
    min_val, max_val = value_range
    # Генерируем случайное число с 1 знаком после запятой
    new_value = round(random.uniform(min_val, max_val), 1) 
    
    payload = {
        "sensor_id": sensor_id,
        "value": new_value,
        # 'timestamp' здесь не нужен, так как он генерируется на сервере
    }
    full_url = f"{BASE_URL}{ENDPOINT}"
    print(f"Sending to {full_url}")

    try:
        response = requests.post(
            full_url, 
            json=payload
        )
        response.raise_for_status() # Вызывает исключение для кодов 4xx/5xx

        print(f"[{datetime.now().strftime('%H:%M:%S')}] OK: SENSOR ID {sensor_id} ({payload.get('value')})")

    except requests.exceptions.RequestException as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: Failed to send data for SENSOR ID {sensor_id}. Ensure API is running.")
        print(f"Error details: {e}")


def main_simulator_loop():
    print("--- 🌡️ СИМУЛЯТОР ДАТЧИКОВ ЗАПУЩЕН ---")
    print(f"Отправка данных каждые {INTERVAL_SECONDS} секунд по адресу: {BASE_URL}{ENDPOINT}")
    
    while True:
        # 1. Генерируем и отправляем температуру
        generate_and_send(SENSOR_TEMP_ID, TEMP_RANGE)
        
        # 2. Генерируем и отправляем влажность
        generate_and_send(SENSOR_HUM_ID, HUM_RANGE)
        
        # 3. Ожидаем следующий интервал
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    # Если база пустая, запустите /api/seed_data, чтобы создать датчики с ID 1 и 2
    main_simulator_loop()