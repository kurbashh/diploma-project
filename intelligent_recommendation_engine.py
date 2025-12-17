"""
Генератор интеллектуальных рекомендаций для корректировки микроклимата.

На основе анализа аномалий датчиков система генерирует:
- Описание проблемы
- Рекомендуемое действие
- Целевое значение параметра
- Обоснование с указанием уверенности
"""

from typing import Dict, Optional, List
from enum import Enum


class SensorType(Enum):
    """Типы датчиков"""
    TEMPERATURE = "Temperature"
    HUMIDITY = "Humidity"
    PRESSURE = "Pressure"


class RecommendationGenerator:
    """
    Генерирует интеллектуальные рекомендации на основе аномалий.
    """
    
    # Нормальные диапазоны для разных типов помещений
    NORMAL_RANGES = {
        'server_room': {
            'temperature': (18, 24),
            'humidity': (40, 60)
        },
        'data_center': {
            'temperature': (16, 20),
            'humidity': (40, 60)
        },
        'laboratory': {
            'temperature': (20, 24),
            'humidity': (45, 65)
        },
        'office': {
            'temperature': (21, 25),
            'humidity': (40, 60)
        },
        'production': {
            'temperature': (18, 28),
            'humidity': (30, 70)
        }
    }
    
    # Рекомендуемые целевые значения
    TARGET_VALUES = {
        'server_room': {
            'temperature': 21.0,
            'humidity': 50.0
        },
        'data_center': {
            'temperature': 18.0,
            'humidity': 50.0
        },
        'laboratory': {
            'temperature': 22.0,
            'humidity': 50.0
        },
        'office': {
            'temperature': 22.5,
            'humidity': 50.0
        },
        'production': {
            'temperature': 23.0,
            'humidity': 50.0
        }
    }
    
    def __init__(self, room_type: str = 'office'):
        """
        Args:
            room_type: Тип помещения (server_room, data_center, office, etc.)
        """
        self.room_type = room_type if room_type in self.NORMAL_RANGES else 'office'
        self.normal_range = self.NORMAL_RANGES[self.room_type]
        self.target_values = self.TARGET_VALUES[self.room_type]
    
    def generate_recommendation(
        self,
        sensor_name: str,
        sensor_type: str,
        current_value: float,
        anomaly_analysis: Dict,
        measurement_history: Optional[List[float]] = None
    ) -> Dict:
        """
        Генерирует рекомендацию на основе аномалии.
        
        Args:
            sensor_name: Название датчика
            sensor_type: Тип датчика (Temperature, Humidity)
            current_value: Текущее значение
            anomaly_analysis: Результаты анализа аномалии
            measurement_history: История измерений (опционально)
        
        Returns:
            {
                'problem_description': str,
                'recommended_action': str,
                'target_value': float,
                'reasoning': str,
                'confidence': float,
                'severity': str,  # 'low', 'medium', 'high', 'critical'
                'priority': int    # 1-5, где 5 = критично
            }
        """
        
        sensor_type_lower = sensor_type.lower()
        
        if 'temperature' in sensor_type_lower:
            return self._generate_temperature_recommendation(
                sensor_name, current_value, anomaly_analysis, measurement_history
            )
        elif 'humidity' in sensor_type_lower:
            return self._generate_humidity_recommendation(
                sensor_name, current_value, anomaly_analysis, measurement_history
            )
        else:
            return self._generate_generic_recommendation(
                sensor_name, sensor_type, current_value, anomaly_analysis
            )
    
    def _generate_temperature_recommendation(
        self,
        sensor_name: str,
        current_value: float,
        anomaly_analysis: Dict,
        history: Optional[List[float]]
    ) -> Dict:
        """Рекомендация для датчика температуры"""
        
        min_temp, max_temp = self.NORMAL_RANGES[self.room_type]['temperature']
        target_temp = self.TARGET_VALUES[self.room_type]['temperature']
        
        # Определяем проблему
        if current_value > max_temp:
            deviation = current_value - max_temp
            severity = self._calculate_severity(deviation, max_temp - min_temp)
            
            problem = f"Temperature is too HIGH ({current_value:.1f}°C, max: {max_temp}°C)"
            action = f"Increase cooling/AC power or improve ventilation"
            reasoning = self._generate_temperature_reasoning(current_value, max_temp, True)
            
            # Целевое значение = средина нормального диапазона
            recommended_target = target_temp
            
        elif current_value < min_temp:
            deviation = min_temp - current_value
            severity = self._calculate_severity(deviation, max_temp - min_temp)
            
            problem = f"Temperature is too LOW ({current_value:.1f}°C, min: {min_temp}°C)"
            action = f"Increase heating power or close air intakes"
            reasoning = self._generate_temperature_reasoning(current_value, min_temp, False)
            
            recommended_target = target_temp
            
        else:
            severity = 'low'
            problem = f"Temperature within normal range ({current_value:.1f}°C)"
            action = "No action required"
            reasoning = "Temperature is within acceptable range"
            recommended_target = current_value
        
        confidence = anomaly_analysis.get('score', 0.5)
        priority = self._severity_to_priority(severity)
        
        return {
            'problem_description': problem,
            'recommended_action': action,
            'target_value': round(recommended_target, 1),
            'reasoning': reasoning,
            'confidence': confidence,
            'severity': severity,
            'priority': priority,
            'sensor_name': sensor_name,
            'current_value': current_value,
            'estimated_time_to_normal': self._estimate_time_to_target(current_value, recommended_target, history)
        }
    
    def _generate_humidity_recommendation(
        self,
        sensor_name: str,
        current_value: float,
        anomaly_analysis: Dict,
        history: Optional[List[float]]
    ) -> Dict:
        """Рекомендация для датчика влажности"""
        
        min_hum, max_hum = self.NORMAL_RANGES[self.room_type]['humidity']
        target_hum = self.TARGET_VALUES[self.room_type]['humidity']
        
        if current_value > max_hum:
            deviation = current_value - max_hum
            severity = self._calculate_severity(deviation, max_hum - min_hum)
            
            problem = f"Humidity is too HIGH ({current_value:.1f}%, max: {max_hum}%)"
            action = f"Increase dehumidification or improve ventilation"
            reasoning = self._generate_humidity_reasoning(current_value, max_hum, True)
            
            recommended_target = target_hum
            
        elif current_value < min_hum:
            deviation = min_hum - current_value
            severity = self._calculate_severity(deviation, max_hum - min_hum)
            
            problem = f"Humidity is too LOW ({current_value:.1f}%, min: {min_hum}%)"
            action = f"Add humidifiers or reduce ventilation"
            reasoning = self._generate_humidity_reasoning(current_value, min_hum, False)
            
            recommended_target = target_hum
            
        else:
            severity = 'low'
            problem = f"Humidity within normal range ({current_value:.1f}%)"
            action = "No action required"
            reasoning = "Humidity is within acceptable range"
            recommended_target = current_value
        
        confidence = anomaly_analysis.get('score', 0.5)
        priority = self._severity_to_priority(severity)
        
        return {
            'problem_description': problem,
            'recommended_action': action,
            'target_value': round(recommended_target, 1),
            'reasoning': reasoning,
            'confidence': confidence,
            'severity': severity,
            'priority': priority,
            'sensor_name': sensor_name,
            'current_value': current_value,
            'risk_of_condensation': self._check_condensation_risk(current_value),
            'estimated_time_to_normal': self._estimate_time_to_target(current_value, recommended_target, history)
        }
    
    def _generate_generic_recommendation(
        self,
        sensor_name: str,
        sensor_type: str,
        current_value: float,
        anomaly_analysis: Dict
    ) -> Dict:
        """Рекомендация для неизвестного датчика"""
        
        score = anomaly_analysis.get('score', 0)
        
        if score > 0.7:
            severity = 'high'
        elif score > 0.5:
            severity = 'medium'
        elif score > 0.3:
            severity = 'low'
        else:
            severity = 'low'
        
        return {
            'problem_description': f"Anomaly detected in {sensor_type}: {current_value}",
            'recommended_action': f"Check {sensor_name} sensor and investigate the anomaly",
            'target_value': current_value,
            'reasoning': f"Anomaly score: {score:.2f}",
            'confidence': score,
            'severity': severity,
            'priority': self._severity_to_priority(severity),
            'sensor_name': sensor_name
        }
    
    def _generate_temperature_reasoning(self, current: float, limit: float, is_high: bool) -> str:
        """Генерирует обоснование для рекомендации по температуре"""
        if is_high:
            diff = current - limit
            if diff > 5:
                return f"Temperature {diff:.1f}°C above normal. Risk of hardware overheating. URGENT ACTION REQUIRED."
            elif diff > 2:
                return f"Temperature {diff:.1f}°C above normal. Cooling system may be insufficient."
            else:
                return f"Temperature {diff:.1f}°C above normal. Monitor cooling system."
        else:
            diff = limit - current
            if diff > 5:
                return f"Temperature {diff:.1f}°C below normal. Check heating system or thermal insulation."
            elif diff > 2:
                return f"Temperature {diff:.1f}°C below normal. Heating may be needed."
            else:
                return f"Temperature {diff:.1f}°C below normal. Monitor heating system."
    
    def _generate_humidity_reasoning(self, current: float, limit: float, is_high: bool) -> str:
        """Генерирует обоснование для рекомендации по влажности"""
        if is_high:
            diff = current - limit
            if diff > 20:
                return f"Humidity {diff:.0f}% above normal. HIGH RISK OF CONDENSATION on electronics!"
            elif diff > 10:
                return f"Humidity {diff:.0f}% above normal. Risk of corrosion and condensation."
            else:
                return f"Humidity {diff:.0f}% above normal. Dehumidification recommended."
        else:
            diff = limit - current
            if diff > 20:
                return f"Humidity {diff:.0f}% below normal. Risk of static electricity and material degradation."
            elif diff > 10:
                return f"Humidity {diff:.0f}% below normal. Humidification recommended."
            else:
                return f"Humidity {diff:.0f}% below normal. Monitor humidity levels."
    
    def _calculate_severity(self, deviation: float, normal_range_width: float) -> str:
        """Определяет серьезность проблемы"""
        relative_deviation = deviation / (normal_range_width / 2)
        
        if relative_deviation > 2.0:
            return 'critical'
        elif relative_deviation > 1.5:
            return 'high'
        elif relative_deviation > 1.0:
            return 'medium'
        else:
            return 'low'
    
    def _severity_to_priority(self, severity: str) -> int:
        """Конвертирует severity в приоритет (1-5)"""
        mapping = {
            'low': 1,
            'medium': 2,
            'high': 4,
            'critical': 5
        }
        return mapping.get(severity, 3)
    
    def _check_condensation_risk(self, humidity: float) -> bool:
        """Проверяет риск конденсации"""
        # Грубая оценка: конденсация при влажности > 80%
        return humidity > 80
    
    def _estimate_time_to_target(
        self,
        current: float,
        target: float,
        history: Optional[List[float]]
    ) -> str:
        """
        Оценивает время достижения целевого значения.
        """
        if history is None or len(history) < 2:
            return "Unknown (insufficient data)"
        
        # Вычисляем скорость изменения за последний час
        last_value = history[-1]
        prev_value = history[-2]
        
        rate = abs(last_value - prev_value)
        
        if rate == 0:
            return "Unable to estimate (no change rate)"
        
        distance = abs(current - target)
        hours_needed = distance / rate
        
        if hours_needed < 1:
            return f"~{int(hours_needed * 60)} minutes"
        elif hours_needed < 24:
            return f"~{int(hours_needed)} hours"
        else:
            return f"~{int(hours_needed / 24)} days"
    
    def bulk_generate_recommendations(
        self,
        sensor_anomalies: List[Dict]
    ) -> List[Dict]:
        """
        Генерирует рекомендации для нескольких датчиков.
        
        Args:
            sensor_anomalies: Список словарей с данными датчиков и аномалиями
        
        Returns:
            Список рекомендаций, отсортированных по приоритету
        """
        recommendations = []
        
        for item in sensor_anomalies:
            if item['anomaly_analysis'].get('is_anomaly', False):
                rec = self.generate_recommendation(
                    sensor_name=item['sensor_name'],
                    sensor_type=item['sensor_type'],
                    current_value=item['current_value'],
                    anomaly_analysis=item['anomaly_analysis'],
                    measurement_history=item.get('measurement_history')
                )
                recommendations.append(rec)
        
        # Сортируем по приоритету (убывание)
        recommendations.sort(key=lambda x: x['priority'], reverse=True)
        
        return recommendations


if __name__ == '__main__':
    # Пример использования
    generator = RecommendationGenerator(room_type='server_room')
    
    # Симуляция аномалии температуры
    anomaly = {
        'is_anomaly': True,
        'score': 0.85,
        'description': 'Temperature anomaly detected'
    }
    
    rec = generator.generate_recommendation(
        sensor_name='Sensor_1_Temp',
        sensor_type='Temperature',
        current_value=28.5,  # Выше нормы
        anomaly_analysis=anomaly,
        measurement_history=[22.0, 22.5, 23.0, 25.0, 28.5]
    )
    
    print("Generated Recommendation:")
    print(f"Problem: {rec['problem_description']}")
    print(f"Action: {rec['recommended_action']}")
    print(f"Target: {rec['target_value']}")
    print(f"Priority: {rec['priority']}/5")
    print(f"Confidence: {rec['confidence']}")
