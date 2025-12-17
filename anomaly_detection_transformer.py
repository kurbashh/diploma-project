"""
Transformer-based методы для анализа временных рядов датчиков микроклимата.

Использует трансформер архитектуру для предсказания аномалий.
Возможные модели:
- Autoencoder-based Transformer (для выявления аномалий)
- Temporal Convolutional Network (для анализа трендов)
"""

from typing import List, Dict
import numpy as np
from datetime import datetime, timedelta


class SimpleTimeSeriesTransformer:
    """
    Упрощённая Transformer-like модель для анализа временных рядов.
    
    Использует attention-подобный механизм для выделения важных точек
    в истории и предсказания аномалий.
    """
    
    def __init__(self, sequence_length: int = 24, threshold: float = 2.0):
        """
        Args:
            sequence_length: Длина последовательности для анализа (часов)
            threshold: Порог для определения аномалии
        """
        self.sequence_length = sequence_length
        self.threshold = threshold
        self.history = []
        self.encoder_weights = None
    
    def _calculate_attention_weights(self, sequence: List[float]) -> List[float]:
        """
        Вычисляет attention weights для каждого элемента в последовательности.
        
        Более важные (необычные) элементы получают больший вес.
        """
        if len(sequence) < 2:
            return [1.0] * len(sequence)
        
        sequence_arr = np.array(sequence)
        mean = np.mean(sequence_arr)
        std = np.std(sequence_arr)
        
        if std == 0:
            return [1.0] * len(sequence)
        
        # Вычисляем отклонение для каждого элемента
        deviations = np.abs((sequence_arr - mean) / std)
        
        # Нормализуем в attention weights
        attention = deviations / (np.sum(deviations) + 1e-8)
        
        return attention.tolist()
    
    def _predict_next_value(self, sequence: List[float]) -> float:
        """
        Предсказывает следующее значение на основе временного ряда.
        
        Использует weighted average с вниманием к последним значениям.
        """
        if len(sequence) == 0:
            return 0.0
        
        sequence_arr = np.array(sequence)
        
        # Простой метод: использовать экспоненциальное сглаживание
        alpha = 0.3  # Smoothing factor
        
        # Начинаем с первого значения
        smoothed = sequence_arr[0]
        
        for value in sequence_arr[1:]:
            smoothed = alpha * value + (1 - alpha) * smoothed
        
        return float(smoothed)
    
    def detect_anomaly(self, measurements: List[float], current_value: float) -> Dict:
        """
        Использует Transformer подход для выявления аномалий.
        
        Процесс:
        1. Берёт последние sequence_length значений
        2. Вычисляет attention для каждого значения
        3. Предсказывает следующее значение
        4. Сравнивает реальное значение с предсказанным
        
        Returns:
            {
                'is_anomaly': bool,
                'score': float,
                'predicted_value': float,
                'description': str,
                'reconstruction_error': float
            }
        """
        if len(measurements) < 2:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'predicted_value': current_value,
                'description': 'Not enough data',
                'reconstruction_error': 0.0
            }
        
        # Берём последние sequence_length значений
        sequence = measurements[-self.sequence_length:] if len(measurements) > self.sequence_length else measurements
        
        # Вычисляем attention weights
        attention_weights = self._calculate_attention_weights(sequence)
        
        # Предсказываем следующее значение
        predicted_value = self._predict_next_value(sequence)
        
        # Вычисляем ошибку реконструкции (reconstruction error)
        error = abs(current_value - predicted_value)
        
        # Нормализуем ошибку
        std_dev = np.std(sequence) if len(sequence) > 1 else 1
        normalized_error = error / (std_dev + 1e-8) if std_dev > 0 else 0
        
        # Определяем аномалию
        is_anomaly = normalized_error > self.threshold
        
        # Score от 0 до 1
        score = min(normalized_error / (self.threshold * 2), 1.0)
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(float(score), 3),
            'predicted_value': round(predicted_value, 2),
            'actual_value': round(current_value, 2),
            'reconstruction_error': round(error, 3),
            'normalized_error': round(normalized_error, 3),
            'attention_summary': f"Last value weight: {round(attention_weights[-1], 3)}, Previous avg: {round(np.mean(attention_weights[:-1]), 3)}",
            'description': f"Predicted {predicted_value:.1f}, got {current_value:.1f}. Error: {error:.2f}"
        }


class TrendAnalysisTransformer:
    """
    Transformer модель для анализа трендов в данных датчиков.
    
    Выявляет:
    - Направление тренда (up, down, stable)
    - Скорость изменения
    - Ускорение/замедление
    - Переломные точки (когда тренд меняется)
    """
    
    def __init__(self, window_size: int = 24):
        """
        Args:
            window_size: Размер окна для анализа тренда (часов)
        """
        self.window_size = window_size
    
    def _calculate_trend(self, sequence: List[float]) -> Dict:
        """
        Вычисляет основные параметры тренда.
        """
        if len(sequence) < 2:
            return {
                'direction': 'insufficient_data',
                'slope': 0.0,
                'acceleration': 0.0
            }
        
        arr = np.array(sequence, dtype=float)
        
        # Простая линейная регрессия для тренда
        x = np.arange(len(arr))
        y = arr
        
        # Коэффициенты для линии: y = slope * x + intercept
        coeffs = np.polyfit(x, y, 1)
        slope = coeffs[0]
        
        # Ускорение (вторая производная)
        if len(arr) >= 3:
            second_deriv = np.polyfit(x, y, 2)[0]  # Коэффициент при x^2
        else:
            second_deriv = 0
        
        # Определяем направление
        if slope > 0.1:
            direction = 'increasing'
        elif slope < -0.1:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        return {
            'direction': direction,
            'slope': round(slope, 4),
            'acceleration': round(second_deriv, 4),
            'first_value': arr[0],
            'last_value': arr[-1],
            'total_change': arr[-1] - arr[0]
        }
    
    def analyze_anomaly(self, measurements: List[float], current_value: float) -> Dict:
        """
        Анализирует аномалию с точки зрения тренда.
        
        Аномалия = внезапный разрыв в тренде или резкое ускорение.
        """
        if len(measurements) < 3:
            return {
                'is_anomaly': False,
                'score': 0.0,
                'description': 'Not enough data for trend analysis'
            }
        
        # Анализируем последние значения
        recent = measurements[-min(self.window_size, len(measurements)):]
        
        trend = self._calculate_trend(recent)
        
        # Предсказываем следующее значение на основе тренда
        arr = np.array(recent, dtype=float)
        x = np.arange(len(arr))
        coeffs = np.polyfit(x, arr, 1)
        expected_next = coeffs[0] * len(arr) + coeffs[1]
        
        # Вычисляем отклонение
        deviation = abs(current_value - expected_next)
        std = np.std(arr)
        
        # Нормализуем
        normalized_deviation = deviation / (std + 1e-8) if std > 0 else 0
        
        # Аномалия если отклонение > 2 std от тренда
        is_anomaly = normalized_deviation > 2.0
        score = min(normalized_deviation / 4, 1.0)
        
        description = f"Trend {trend['direction']}: expected ~{expected_next:.1f}, got {current_value:.1f}"
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(score, 3),
            'description': description,
            'trend': trend,
            'expected_value': round(expected_next, 2),
            'actual_value': current_value,
            'deviation_from_trend': round(deviation, 2)
        }


class EnsembleAnomalyDetector:
    """
    Ensemble метод: комбинирует несколько Transformer-подобных методов.
    """
    
    def __init__(self):
        self.time_series_detector = SimpleTimeSeriesTransformer()
        self.trend_detector = TrendAnalysisTransformer()
    
    def detect_anomaly(self, measurements: List[float], current_value: float) -> Dict:
        """
        Использует несколько методов и комбинирует результаты.
        """
        # Получаем результаты от обоих методов
        ts_result = self.time_series_detector.detect_anomaly(measurements, current_value)
        trend_result = self.trend_detector.analyze_anomaly(measurements, current_value)
        
        # Комбинируем скоры (среднее)
        combined_score = (ts_result['score'] + trend_result['score']) / 2
        
        # Аномалия если хотя бы один метод её выявил
        is_anomaly = ts_result['is_anomaly'] or trend_result['is_anomaly']
        
        return {
            'is_anomaly': is_anomaly,
            'score': round(combined_score, 3),
            'time_series_score': ts_result['score'],
            'trend_score': trend_result['score'],
            'models_agree': ts_result['is_anomaly'] == trend_result['is_anomaly'],
            'time_series_analysis': ts_result,
            'trend_analysis': trend_result,
            'description': f"Ensemble detection: anomaly={is_anomaly}, confidence={combined_score:.2f}"
        }


# Инициализация глобальных моделей
time_series_detector = SimpleTimeSeriesTransformer()
trend_detector = TrendAnalysisTransformer()
ensemble_detector = EnsembleAnomalyDetector()


if __name__ == '__main__':
    # Примеры использования
    test_measurements = [20.0, 20.5, 21.0, 20.8, 21.2, 20.9, 21.0, 35.0, 21.1]
    
    print("=== Time Series Transformer ===")
    result = time_series_detector.detect_anomaly(test_measurements[:-1], test_measurements[-1])
    print(f"Anomaly: {result['is_anomaly']}, Score: {result['score']}")
    print(f"Description: {result['description']}\n")
    
    print("=== Ensemble Detector ===")
    result = ensemble_detector.detect_anomaly(test_measurements[:-1], test_measurements[-1])
    print(f"Anomaly: {result['is_anomaly']}, Score: {result['score']}")
    print(f"Models agree: {result['models_agree']}")
