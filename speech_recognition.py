"""
Модель распознавания речи для голосового управления системой микроклимата.
Использует Whisper для транскрибирования аудио.
"""

import os
from typing import Dict, Optional
import json
from datetime import datetime


class SpeechRecognizer:
    """
    Распознавание речи с использованием Whisper.
    Преобразует аудиофайлы в текст.
    """
    
    def __init__(self, model_size: str = "base"):
        """
        Args:
            model_size: Размер модели Whisper ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.model_size = model_size
        self.model = None
        self._try_load_model()
    
    def _try_load_model(self):
        """Попытка загрузить модель Whisper"""
        try:
            import whisper
            self.model = whisper.load_model(self.model_size)
        except ImportError:
            print("⚠️ Warning: whisper not installed. Speech recognition unavailable")
        except Exception as e:
            print(f"⚠️ Warning: Failed to load Whisper model: {e}")
    
    def transcribe(self, audio_file_path: str, language: str = None) -> Dict:
        """
        Транскрибирует аудиофайл в текст.
        
        Args:
            audio_file_path: Путь к аудиофайлу (mp3, wav, m4a, flac)
            language: Код языка ('ru', 'en') или None для автоопределения
        
        Returns:
            {
                'text': str,
                'language': str,
                'confidence': float,
                'duration': float,
                'segments': list
            }
        """
        if not self.model:
            return {
                'text': '',
                'error': 'Model not loaded',
                'language': None,
                'confidence': 0.0
            }
        
        if not os.path.exists(audio_file_path):
            return {
                'text': '',
                'error': f'File not found: {audio_file_path}',
                'language': None,
                'confidence': 0.0
            }
        
        try:
            result = self.model.transcribe(
                audio_file_path,
                language=language,
                verbose=False
            )
            
            return {
                'text': result.get('text', '').strip(),
                'language': result.get('language', 'unknown'),
                'confidence': self._estimate_confidence(result),
                'duration': result.get('duration', 0),
                'segments': [
                    {
                        'start': seg.get('start', 0),
                        'end': seg.get('end', 0),
                        'text': seg.get('text', '').strip()
                    }
                    for seg in result.get('segments', [])
                ]
            }
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return {
                'text': '',
                'error': str(e),
                'language': None,
                'confidence': 0.0
            }
    
    def _estimate_confidence(self, result: Dict) -> float:
        """
        Оценивает уверенность в транскрибировании.
        Высчитывается на основе no_speech_prob в сегментах.
        """
        segments = result.get('segments', [])
        if not segments:
            return 0.0
        
        # Берём среднюю вероятность что это НЕ молчание
        no_speech_probs = [seg.get('no_speech_prob', 0) for seg in segments]
        avg_no_speech = sum(no_speech_probs) / len(no_speech_probs) if no_speech_probs else 0
        confidence = 1 - avg_no_speech
        
        return round(min(max(confidence, 0), 1), 3)


class VoiceCommandParser:
    """
    Парсер голосовых команд для управления системой микроклимата.
    Преобразует распознанный текст в команды.
    """
    
    def __init__(self):
        # Словари команд на разных языках
        self.commands = {
            'temperature_up': {
                'ru': ['повысить температуру', 'сделай теплее', 'добавь тепла'],
                'en': ['increase temperature', 'make it warmer', 'add heat']
            },
            'temperature_down': {
                'ru': ['понизить температуру', 'сделай прохладнее', 'добавь прохлады'],
                'en': ['decrease temperature', 'make it cooler', 'add cooling']
            },
            'humidity_up': {
                'ru': ['повысить влажность', 'добавь влаги', 'сделай влажнее'],
                'en': ['increase humidity', 'add moisture', 'make it humid']
            },
            'humidity_down': {
                'ru': ['понизить влажность', 'уменьши влагу', 'сделай суше'],
                'en': ['decrease humidity', 'remove moisture', 'make it dry']
            },
            'ventilation_on': {
                'ru': ['включи вентиляцию', 'открой окно', 'проветри'],
                'en': ['turn on ventilation', 'open window', 'ventilate']
            },
            'ventilation_off': {
                'ru': ['выключи вентиляцию', 'закрой окно'],
                'en': ['turn off ventilation', 'close window']
            },
            'status': {
                'ru': ['какой климат', 'как находиться', 'дай статус'],
                'en': ['what is temperature', 'how are conditions', 'give status']
            }
        }
    
    def parse_command(self, text: str, detected_language: str = 'en') -> Dict:
        """
        Парсит текст и определяет команду.
        
        Args:
            text: Распознанный текст
            detected_language: Детектированный язык ('ru' или 'en')
        
        Returns:
            {
                'command': str,
                'confidence': float,
                'parameters': dict,
                'raw_text': str
            }
        """
        text_lower = text.lower()
        best_command = None
        best_confidence = 0
        
        for command, lang_dict in self.commands.items():
            phrases = lang_dict.get(detected_language, []) + lang_dict.get('en', [])
            
            for phrase in phrases:
                if phrase in text_lower:
                    confidence = len(phrase) / len(text_lower)  # Простая эвристика
                    if confidence > best_confidence:
                        best_command = command
                        best_confidence = confidence
        
        if not best_command:
            return {
                'command': 'unknown',
                'confidence': 0.0,
                'parameters': {},
                'raw_text': text
            }
        
        # Извлекаем параметры из команды
        parameters = self._extract_parameters(best_command, text_lower)
        
        return {
            'command': best_command,
            'confidence': round(min(best_confidence, 1.0), 3),
            'parameters': parameters,
            'raw_text': text
        }
    
    def _extract_parameters(self, command: str, text: str) -> Dict:
        """
        Извлекает параметры из текста команды.
        Например, значение для повышения температуры.
        """
        parameters = {}
        
        # Ищем числа в тексте
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            parameters['value'] = int(numbers[0])
        
        # Базовые параметры для каждой команды
        if 'temperature' in command:
            parameters['type'] = 'temperature'
            if 'up' in command:
                parameters['action'] = 'increase'
            else:
                parameters['action'] = 'decrease'
        
        elif 'humidity' in command:
            parameters['type'] = 'humidity'
            if 'up' in command:
                parameters['action'] = 'increase'
            else:
                parameters['action'] = 'decrease'
        
        elif 'ventilation' in command:
            parameters['type'] = 'ventilation'
            parameters['action'] = 'on' if 'on' in command else 'off'
        
        return parameters


class VoiceInteractionManager:
    """
    Управляет всем процессом голосового взаимодействия:
    - Распознавание речи
    - Парсинг команд
    - Логирование
    """
    
    def __init__(self):
        self.recognizer = SpeechRecognizer()
        self.command_parser = VoiceCommandParser()
        self.interaction_history = []
    
    def process_voice_input(self, audio_file_path: str) -> Dict:
        """
        Полный процесс обработки голосового ввода.
        
        Returns:
            {
                'transcript': str,
                'detected_language': str,
                'command': str,
                'parameters': dict,
                'confidence_speech': float,
                'confidence_command': float,
                'timestamp': str
            }
        """
        # Шаг 1: Распознавание речи
        speech_result = self.recognizer.transcribe(audio_file_path)
        
        if 'error' in speech_result:
            return speech_result
        
        transcript = speech_result['text']
        language = speech_result['language']
        
        # Маппируем коды языков Whisper на наши
        language_map = {'ru': 'ru', 'en': 'en'}
        detected_lang = language_map.get(language[:2], 'en')
        
        # Шаг 2: Парсинг команды
        command_result = self.command_parser.parse_command(transcript, detected_lang)
        
        # Шаг 3: Логирование
        interaction = {
            'transcript': transcript,
            'detected_language': detected_lang,
            'command': command_result['command'],
            'parameters': command_result['parameters'],
            'confidence_speech': speech_result['confidence'],
            'confidence_command': command_result['confidence'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.interaction_history.append(interaction)
        
        return interaction
    
    def get_history(self, limit: int = 10) -> list:
        """Получает историю последних взаимодействий"""
        return self.interaction_history[-limit:]
    
    def clear_history(self):
        """Очищает историю взаимодействий"""
        self.interaction_history = []


# Инициализация глобального менеджера
voice_manager = VoiceInteractionManager()


if __name__ == '__main__':
    # Простой тест (если есть аудиофайл)
    test_audio_path = "test_audio.wav"
    
    if os.path.exists(test_audio_path):
        print("=== Speech Recognition ===")
        result = voice_manager.process_voice_input(test_audio_path)
        print(json.dumps(result, indent=2))
    else:
        print(f"Test audio file not found: {test_audio_path}")
        print("\nYou can test the system by providing an audio file.")
