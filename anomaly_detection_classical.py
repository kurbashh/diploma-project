"""
Классические методы анализа аномалий в данных датчиков микроклимата.

Методы:
- Скользящее среднее (Moving Average)
- Стандартное отклонение (Z-score)
- Seasonal Decomposition
- Изолирующий лес (Isolation Forest)
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import IsolationForest
import statistics


class MovingAverageAnomalyDetector:
    """
    Классический метод: скользящее среднее для выявления отклонений.
    
    Идея: если текущее значение значительно отличается от среднего
    за последний период, это аномалия.
    """
    
    def __init__(self, window_size: int = 24, threshold_std: float = 2.0):
        """
        Args:
            window_size: Размер окна для расчёта среднего (часов)
            threshold_std: Количество стандартных отклонений для порога
        """
        self.window_size = window_size
        self.threshold_std = threshold_std
    
    def detect_anomaly(self, measurements: List[float], current_value: float) -> Dict:
        """
        Определяет, является ли текущее значение аномалией.
        
        Args:
            measurements: История измерений
            current_value: Текущее значение
        
        Returns:
            {
                'is_anomaly': bool,
                'score': float (0-1),
                'deviation': float,
                'description': str
            }
        """
        if len(measurements) < 2:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'deviation': 0.0,
                'description': 'Not enough data for analysis'
            }
        
        # Берём последние window_size значений
        window = measurements[-self.window_size:] if len(measurements) > self.window_size else measurements
        
        avg = statistics.mean(window)
        std = statistics.stdev(window) if len(window) > 1 else 0
        
        # Вычисляем z-score для текущего значения
        if std > 0:
            z_score = abs((current_value - avg) / std)
        else:
            z_score = 0
        
        # Аномалия если z_score > threshold
        is_anomaly = z_score > self.threshold_std
        
        # Score от 0 до 1
        score = min(z_score / (self.threshold_std * 2), 1.0)
        deviation = current_value - avg
        
        # Описание
        if is_anomaly:
            if deviation > 0:
                description = f"Value {current_value:.1f} is significantly HIGHER than average {avg:.1f}"
            else:
                description = f"Value {current_value:.1f} is significantly LOWER than average {avg:.1f}"
        else:
            description = f"Value {current_value:.1f} is within normal range (avg: {avg:.1f}, std: {std:.1f})"
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(score, 3),
            'deviation': round(deviation, 3),
            'description': description,
            'avg': round(avg, 1),
            'std': round(std, 1)
        }


class IsolationForestAnomalyDetector:
    """
    Машинное обучение метод: Isolation Forest для выявления аномалий.
    
    Работает с многомерными данными (несколько датчиков одновременно).
    """
    
    def __init__(self, contamination: float = 0.1):
        """
        Args:
            contamination: Доля аномалий в данных (0.1 = 10%)
        """
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.is_trained = False
        self.scaler_params = None
    
    def train(self, measurements_history: List[List[float]]):
        """
        Обучает модель на исторических данных.
        
        Args:
            measurements_history: [[temp1, humidity1, ...], [temp2, humidity2, ...], ...]
        """
        if len(measurements_history) < 10:
            print("Warning: Need at least 10 samples to train Isolation Forest")
            return
        
        X = np.array(measurements_history)
        
        # Нормализация
        self.scaler_params = {
            'means': X.mean(axis=0),
            'stds': X.std(axis=0)
        }
        
        X_normalized = (X - self.scaler_params['means']) / (self.scaler_params['stds'] + 1e-8)
        
        self.model.fit(X_normalized)
        self.is_trained = True
    
    def detect_anomaly(self, current_measurement: List[float]) -> Dict:
        """
        Определяет, является ли текущее измерение аномалией.
        
        Args:
            current_measurement: [temp, humidity, ...]
        
        Returns:
            {
                'is_anomaly': bool,
                'score': float (0-1),
                'description': str
            }
        """
        if not self.is_trained:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'description': 'Model not trained'
            }
        
        X = np.array(current_measurement).reshape(1, -1)
        
        # Нормализация
        X_normalized = (X - self.scaler_params['means']) / (self.scaler_params['stds'] + 1e-8)
        
        # Предсказание (-1 = аномалия, 1 = норма)
        prediction = self.model.predict(X_normalized)[0]
        
        # Anomaly score (расстояние от decision boundary)
        # Отрицательный = аномалия, положительный = норма
        anomaly_score = -self.model.score_samples(X_normalized)[0]
        
        is_anomaly = prediction == -1
        
        # Нормализуем score в диапазон 0-1
        normalized_score = 1 / (1 + np.exp(-anomaly_score))
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(float(normalized_score), 3),
            'description': 'Anomaly detected' if is_anomaly else 'Normal measurement',
            'raw_score': round(float(anomaly_score), 3)
        }


class SeasonalAnomalyDetector:
    """
    Анализ сезонных паттернов для выявления аномалий.
    
    Идея: микроклимат имеет суточные и недельные циклы,
    выход за рамки цикла = аномалия.
    """
    
    def __init__(self, cycle_hours: int = 24):
        """
        Args:
            cycle_hours: Длина сезонного цикла в часах (24 = суточный)
        """
        self.cycle_hours = cycle_hours
        self.seasonal_means = {}  # Средние значения для каждого часа дня
        self.seasonal_stds = {}
        self.is_trained = False
    
    def train(self, measurements: List[Tuple[datetime, float]]):
        """
        Обучается на исторических данных с временными метками.
        
        Args:
            measurements: [(timestamp, value), (timestamp, value), ...]
        """
        # Группируем по часам дня
        hourly_values = {h: [] for h in range(24)}
        
        for timestamp, value in measurements:
            hour = timestamp.hour
            hourly_values[hour].append(value)
        
        # Вычисляем среднее и стандартное отклонение для каждого часа
        for hour, values in hourly_values.items():
            if values:
                self.seasonal_means[hour] = statistics.mean(values)
                self.seasonal_stds[hour] = statistics.stdev(values) if len(values) > 1 else 0
        
        self.is_trained = True
    
    def detect_anomaly(self, timestamp: datetime, current_value: float) -> Dict:
        """
        Проверяет, соответствует ли значение сезонному паттерну.
        
        Returns:
            {
                'is_anomaly': bool,
                'score': float,
                'seasonal_mean': float,
                'description': str
            }
        """
        if not self.is_trained:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'description': 'Model not trained'
            }
        
        hour = timestamp.hour
        seasonal_mean = self.seasonal_means.get(hour, None)
        seasonal_std = self.seasonal_stds.get(hour, 0)
        
        if seasonal_mean is None:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'description': 'No seasonal data for this hour'
            }
        
        # Z-score based on seasonal pattern
        if seasonal_std > 0:
            z_score = abs((current_value - seasonal_mean) / seasonal_std)
        else:
            z_score = 0
        
        is_anomaly = z_score > 2.5
        score = min(z_score / 5, 1.0)
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(score, 3),
            'seasonal_mean': round(seasonal_mean, 1),
            'deviation_from_seasonal': round(current_value - seasonal_mean, 2),
            'description': f"Hour {hour}: expected {seasonal_mean:.1f}, got {current_value:.1f}"
        }


# Инициализация глобальных анализаторов
moving_avg_detector = MovingAverageAnomalyDetector()
isolation_forest_detector = IsolationForestAnomalyDetector()
seasonal_detector = SeasonalAnomalyDetector()


if __name__ == '__main__':
    # Примеры использования
    test_measurements = [20.0, 20.5, 21.0, 20.8, 21.2, 20.9, 35.0, 21.1]  # Последнее = аномалия
    
    print("=== Moving Average Anomaly Detection ===")
    for value in test_measurements:
        result = moving_avg_detector.detect_anomaly(test_measurements[:test_measurements.index(value)+1], value)
        print(f"Value: {value} → Anomaly: {result['is_anomaly']}, Score: {result['score']}")
