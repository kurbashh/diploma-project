"""
Модуль распознавания голосовых команд для управления уведомлениями о микроклимате.
Использует Whisper для транскрибирования и распознавания команд подтверждения/отклонения.

Функции:
- Распознавание команд подтверждения/отклонения уведомлений (DIPLOMA CRITERION 4)
- Запрос информации об аномалии
- Голосовые команды для изменения параметров рекомендации
"""

import os
from typing import Dict, Optional, List
import json
from datetime import datetime
from enum import Enum


class NotificationCommand(str, Enum):
    """Перечисление возможных голосовых команд для уведомлений"""
    CONFIRM = "confirm"  # Подтверждение: "да", "согласен", "yes"
    REJECT = "reject"    # Отклонение: "нет", "отклоняю", "no"
    MODIFY = "modify"    # Изменить: "изменить", "change"
    REQUEST_INFO = "request_info"  # Информация: "объясни", "explain"
    REQUEST_REPORT = "request_report"  # Отчет: "отчет", "report"
    UNKNOWN = "unknown"  # Неизвестная команда


class NotificationVoiceCommandParser:
    """
    Парсер голосовых команд для управления уведомлениями.
    Распознаёт команды подтверждения/отклонения/модификации рекомендаций.
    """
    
    def __init__(self):
        """Инициализация парсера с мультиязычной поддержкой"""
        # Команды для подтверждения действия
        self.confirmation_commands = {
            NotificationCommand.CONFIRM: {
                'ru': ['да', 'согласен', 'согласна', 'подтверждаю', 'нормально', 'ладно', 'окей', 'ok'],
                'en': ['yes', 'ok', 'confirm', 'approved', 'go ahead', 'alright', 'sure']
            },
            NotificationCommand.REJECT: {
                'ru': ['нет', 'отклоняю', 'не нужно', 'отменить', 'отмена', 'no', 'cancel'],
                'en': ['no', 'reject', 'cancel', 'skip', 'decline', 'not now', 'ignore']
            },
            NotificationCommand.MODIFY: {
                'ru': ['изменить', 'изменить значение', 'другое значение', 'измени', 'поменяй'],
                'en': ['modify', 'change', 'different value', 'adjust', 'set to']
            },
            NotificationCommand.REQUEST_INFO: {
                'ru': ['информация', 'подробнее', 'объясни', 'почему', 'как это', 'info', 'explain', 'why'],
                'en': ['info', 'explain', 'why', 'details', 'more information', 'tell me more']
            },
            NotificationCommand.REQUEST_REPORT: {
                'ru': ['отчет', 'история', 'график', 'статистика', 'покажи', 'data', 'report'],
                'en': ['report', 'history', 'graph', 'statistics', 'show data', 'data']
            }
        }
    
    def parse_command(self, transcript: str, language: str = 'en') -> Dict:
        """
        Парсит голосовую команду для управления уведомлением.
        
        Args:
            transcript: Распознанный текст от Whisper
            language: Определённый язык ('ru' или 'en')
        
        Returns:
            {
                'command': NotificationCommand (или str),
                'confidence': float (0-1),
                'matched_keywords': list,
                'raw_transcript': str,
                'language_detected': str
            }
        """
        transcript_lower = transcript.lower().strip()
        
        if not transcript_lower:
            return {
                'command': NotificationCommand.UNKNOWN.value,
                'confidence': 0.0,
                'matched_keywords': [],
                'raw_transcript': transcript,
                'language_detected': language
            }
        
        best_command = None
        best_confidence = 0.0
        matched_keywords = []
        
        # Проходим по всем командам и ищем совпадения
        for command, lang_dict in self.confirmation_commands.items():
            # Собираем фразы для данного языка (приоритет - выбранный язык)
            phrases = lang_dict.get(language, [])
            if not phrases:
                phrases = lang_dict.get('en', [])
            
            for phrase in phrases:
                if phrase in transcript_lower:
                    # Confidence = доля совпадающей фразы в общем тексте
                    confidence = len(phrase) / len(transcript_lower)
                    
                    if confidence > best_confidence:
                        best_command = command
                        best_confidence = confidence
                        matched_keywords = [phrase]
        
        if not best_command:
            return {
                'command': NotificationCommand.UNKNOWN.value,
                'confidence': 0.0,
                'matched_keywords': [],
                'raw_transcript': transcript,
                'language_detected': language
            }
        
        return {
            'command': best_command.value,
            'confidence': min(best_confidence, 1.0),
            'matched_keywords': matched_keywords,
            'raw_transcript': transcript,
            'language_detected': language
        }
    
    def extract_numeric_value(self, transcript: str) -> Optional[float]:
        """
        Извлекает числовое значение из команды изменения.
        Например: "измени на 23 градуса" -> 23.0
        
        Args:
            transcript: Распознанный текст
        
        Returns:
            float (или None если не найдено)
        """
        import re
        # Ищем числа (включая с точкой/запятой)
        numbers = re.findall(r'\d+[.,]?\d*', transcript)
        if numbers:
            value_str = numbers[0].replace(',', '.')
            try:
                return float(value_str)
            except ValueError:
                return None
        return None


class SpeechRecognizerNotifications:
    """
    Распознавание речи с использованием Whisper специально для уведомлений.
    Преобразует аудиофайлы в текст с оптимизацией для коротких команд.
    """
    
    def __init__(self, model_size: str = "tiny"):
        """
        Args:
            model_size: Размер модели Whisper ('tiny', 'base', 'small', 'medium', 'large')
                        'tiny' рекомендуется для коротких команд (быстрее)
        """
        self.model_size = model_size
        self.model = None
        self._try_load_model()
        self.is_available = self.model is not None
    
    def _try_load_model(self):
        """Попытка загрузить модель Whisper"""
        try:
            import whisper
            self.model = whisper.load_model(self.model_size)
        except ImportError:
            print("[WARNING] whisper not installed. Voice notification commands unavailable")
            print("   Install with: pip install openai-whisper")
        except Exception as e:
            print(f"[WARNING] Failed to load Whisper model: {e}")
    
    def transcribe(self, audio_file_path: str, language: str = None) -> Dict:
        """
        Транскрибирует аудиофайл в текст.
        Оптимизировано для коротких команд.
        
        Args:
            audio_file_path: Путь к аудиофайлу (mp3, wav, m4a, flac)
            language: Код языка ('ru', 'en') или None для автоопределения
        
        Returns:
            {
                'text': str,
                'language': str,
                'confidence': float (0-1),
                'duration': float (в секундах),
                'success': bool
            }
        """
        if not self.model:
            return {
                'text': '',
                'language': None,
                'confidence': 0.0,
                'duration': 0.0,
                'success': False,
                'error': 'Model not loaded'
            }
        
        if not os.path.exists(audio_file_path):
            return {
                'text': '',
                'language': None,
                'confidence': 0.0,
                'duration': 0.0,
                'success': False,
                'error': f'File not found: {audio_file_path}'
            }
        
        try:
            result = self.model.transcribe(
                audio_file_path,
                language=language,
                verbose=False,
                fp16=False  # Улучшенная стабильность на CPU
            )
            
            text = result.get('text', '').strip()
            language_detected = result.get('language', 'unknown')
            confidence = self._estimate_confidence(result)
            duration = result.get('duration', 0.0)
            
            return {
                'text': text,
                'language': language_detected,
                'confidence': confidence,
                'duration': duration,
                'success': bool(text)
            }
        
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return {
                'text': '',
                'language': None,
                'confidence': 0.0,
                'duration': 0.0,
                'success': False,
                'error': str(e)
            }
    
    def _estimate_confidence(self, result: Dict) -> float:
        """
        Оценивает уверенность в транскрибировании.
        Основана на вероятности что это не молчание.
        """
        segments = result.get('segments', [])
        if not segments:
            return 0.0
        
        # Берём среднюю вероятность что это НЕ молчание
        no_speech_probs = [seg.get('no_speech_prob', 0) for seg in segments]
        if not no_speech_probs:
            return 0.0
        
        avg_no_speech = sum(no_speech_probs) / len(no_speech_probs)
        confidence = 1.0 - avg_no_speech
        
        return round(min(max(confidence, 0), 1), 3)


class VoiceNotificationManager:
    """
    Главный менеджер для обработки голосовых команд уведомлений.
    
    Полный процесс:
    1. Распознавание речи (Whisper) - DIPLOMA CRITERION 4
    2. Парсинг команды (confirm/reject/modify/info/report)
    3. Логирование взаимодействия
    """
    
    def __init__(self):
        """Инициализация менеджера"""
        self.recognizer = SpeechRecognizerNotifications()
        self.command_parser = NotificationVoiceCommandParser()
        self.interaction_history: List[Dict] = []
    
    def process_notification_voice_input(self, 
                                        audio_file_path: str, 
                                        notification_id: int = None,
                                        sensor_id: int = None) -> Dict:
        """
        Полный процесс обработки голосовой команды управления уведомлением.
        
        Шаги:
        1. Распознаёт речь из аудиофайла (Whisper) - DIPLOMA CRITERION 4
        2. Парсит команду (confirm/reject/modify/request_info/request_report)
        3. Возвращает результат с метаданными
        
        Args:
            audio_file_path: Путь к аудиофайлу (.wav, .mp3, .m4a и т.д.)
            notification_id: ID уведомления которым управляем (опционально)
            sensor_id: ID сенсора связанного с уведомлением (опционально)
        
        Returns:
            {
                'success': bool,
                'transcript': str,  # Что распознал Whisper
                'detected_language': str,  # 'ru' или 'en'
                'command': str,  # 'confirm', 'reject', 'modify', 'request_info', 'request_report', 'unknown'
                'confidence_speech': float,  # 0-1 уверенность Whisper
                'confidence_command': float,  # 0-1 уверенность парсера команды
                'extracted_value': Optional[float],  # Извлечённое число (для modify)
                'notification_id': Optional[int],
                'sensor_id': Optional[int],
                'timestamp': str,  # ISO8601
                'error': Optional[str]  # Если есть ошибка
            }
        """
        try:
            # Проверка что Whisper доступен
            if not self.recognizer.is_available:
                return {
                    'success': False,
                    'error': 'Speech recognition not available (Whisper not loaded)',
                    'command': NotificationCommand.UNKNOWN.value,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # Шаг 1: Распознавание речи (Whisper) - DIPLOMA CRITERION 4
            speech_result = self.recognizer.transcribe(audio_file_path)
            
            if not speech_result.get('success'):
                return {
                    'success': False,
                    'error': speech_result.get('error', 'Unknown speech recognition error'),
                    'command': NotificationCommand.UNKNOWN.value,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            transcript = speech_result['text']
            language = speech_result['language']
            speech_confidence = speech_result['confidence']
            
            # Маппируем коды языков Whisper на наши
            language_map = {
                'ru': 'ru',
                'en': 'en',
            }
            detected_lang = language_map.get(language[:2], 'en')
            
            # Шаг 2: Парсинг команды
            command_result = self.command_parser.parse_command(transcript, detected_lang)
            command = command_result['command']
            command_confidence = command_result['confidence']
            
            # Шаг 3: Извлечение числового значения (если команда modify)
            extracted_value = None
            if command == NotificationCommand.MODIFY.value:
                extracted_value = self.command_parser.extract_numeric_value(transcript)
            
            # Шаг 4: Подготовка результата
            interaction = {
                'success': True,
                'transcript': transcript,
                'detected_language': detected_lang,
                'command': command,
                'confidence_speech': speech_confidence,
                'confidence_command': command_confidence,
                'extracted_value': extracted_value,
                'notification_id': notification_id,
                'sensor_id': sensor_id,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Шаг 5: Логирование
            self.interaction_history.append(interaction)
            
            return interaction
        
        except Exception as e:
            print(f"Error processing notification voice input: {e}")
            return {
                'success': False,
                'error': str(e),
                'command': NotificationCommand.UNKNOWN.value,
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def get_history(self, limit: int = 10, notification_id: int = None) -> List[Dict]:
        """
        Получает историю взаимодействий.
        
        Args:
            limit: Максимум результатов
            notification_id: Фильтр по уведомлению (опционально)
        
        Returns:
            List[Dict] с последними взаимодействиями
        """
        history = self.interaction_history[-limit:]
        
        if notification_id:
            history = [h for h in history if h.get('notification_id') == notification_id]
        
        return history
    
    def clear_history(self):
        """Очищает историю взаимодействий"""
        self.interaction_history = []
    
    def get_stats(self) -> Dict:
        """
        Получает статистику по голосовым командам.
        
        Returns:
            {
                'total_interactions': int,
                'commands_distribution': Dict[str, int],
                'avg_speech_confidence': float,
                'avg_command_confidence': float
            }
        """
        if not self.interaction_history:
            return {
                'total_interactions': 0,
                'commands_distribution': {},
                'avg_speech_confidence': 0.0,
                'avg_command_confidence': 0.0
            }
        
        commands = {}
        total_speech_conf = 0.0
        total_cmd_conf = 0.0
        successful = 0
        
        for interaction in self.interaction_history:
            if interaction.get('success'):
                cmd = interaction.get('command', 'unknown')
                commands[cmd] = commands.get(cmd, 0) + 1
                total_speech_conf += interaction.get('confidence_speech', 0)
                total_cmd_conf += interaction.get('confidence_command', 0)
                successful += 1
        
        avg_speech = total_speech_conf / successful if successful > 0 else 0
        avg_cmd = total_cmd_conf / successful if successful > 0 else 0
        
        return {
            'total_interactions': len(self.interaction_history),
            'successful_interactions': successful,
            'commands_distribution': commands,
            'avg_speech_confidence': round(avg_speech, 3),
            'avg_command_confidence': round(avg_cmd, 3)
        }


# Глобальный инстанс для использования в приложении
voice_notification_manager = VoiceNotificationManager()


if __name__ == '__main__':
    # Демонстрация работы парсера команд
    print("=== Voice Notification Command Parser Demo ===\n")
    
    parser = NotificationVoiceCommandParser()
    
    test_cases = [
        ("да", "ru"),
        ("yes", "en"),
        ("не нужно", "ru"),
        ("no thanks", "en"),
        ("измени на 23", "ru"),
        ("set to 24", "en"),
        ("почему нельзя", "ru"),
        ("explain please", "en"),
    ]
    
    for transcript, lang in test_cases:
        result = parser.parse_command(transcript, lang)
        print(f"Input: '{transcript}' (language: {lang})")
        print(f"  Command: {result['command']}")
        print(f"  Confidence: {result['confidence']:.3f}")
        if result['matched_keywords']:
            print(f"  Matched: {', '.join(result['matched_keywords'])}")
        print()
