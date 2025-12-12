# backend/src/utils/helpers.py
"""
Вспомогательные функции для TestOps Copilot
"""
import re
import hashlib
import uuid
from typing import Any, Dict, List
from datetime import datetime, timedelta


def generate_testcase_id(title: str) -> str:
    """
    Генерация уникального ID для тест-кейса на основе заголовка
    """
    # Создаем hash из заголовка
    title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
    
    # Генерируем UUID
    unique_part = str(uuid.uuid4())[:8]
    
    return f"TC-{title_hash}-{unique_part}"


def format_python_code(code: str) -> str:
    """
    Форматирование Python кода (базовая очистка)
    """
    # Удаляем лишние пустые строки
    lines = code.split('\n')
    formatted_lines = []
    
    for line in lines:
        stripped_line = line.rstrip()
        if stripped_line or (formatted_lines and formatted_lines[-1].strip()):
            formatted_lines.append(stripped_line)
    
    # Убеждаемся, что в конце файла есть пустая строка
    if formatted_lines and formatted_lines[-1]:
        formatted_lines.append('')
    
    return '\n'.join(formatted_lines)


def extract_json_from_text(text: str) -> Dict[str, Any]:
    """
    Извлечение JSON из текстового ответа LLM
    """
    import json
    
    # Пытаемся найти JSON блок
    json_patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'(\{.*\})',
        r'(\[.*\])'
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        for match in matches:
            try:
                return json.loads(match.strip())
            except json.JSONDecodeError:
                continue
    
    # Если не нашли, пытаемся распарсить весь текст
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        raise ValueError("Не удалось извлечь JSON из текста")


def calculate_estimated_time(testcases_count: int, test_type: str) -> int:
    """
    Расчет примерного времени выполнения
    """
    base_times = {
        "manual_ui": 30,  # 30 секунд на тест-кейс
        "manual_api": 25,
        "auto_ui": 45,
        "auto_api": 35
    }
    
    base_time = base_times.get(test_type, 30)
    
    # Нелинейное увеличение времени при большом количестве тест-кейсов
    if testcases_count <= 10:
        multiplier = 1.0
    elif testcases_count <= 30:
        multiplier = 0.9
    else:
        multiplier = 0.8
    
    estimated = int(base_time * testcases_count * multiplier)
    
    # Минимальное и максимальное время
    return max(60, min(estimated, 1800))  # от 1 минуты до 30 минут


def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def sanitize_filename(filename: str) -> str:
    """Очистка имени файла от недопустимых символов"""
    # Заменяем недопустимые символы на подчеркивания
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Удаляем лишние подчеркивания
    sanitized = re.sub(r'_+', '_', sanitized)
    # Удаляем подчеркивания в начале и конце
    sanitized = sanitized.strip('_')
    
    # Если имя файла стало пустым, возвращаем дефолтное
    if not sanitized:
        sanitized = f"file_{int(datetime.now().timestamp())}"
    
    return sanitized


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Разделение списка на чанки"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def format_duration(seconds: int) -> str:
    """Форматирование времени в читаемый вид"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes} мин {seconds} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч {minutes} мин"


def get_file_extension(filename: str) -> str:
    """Получение расширения файла"""
    return filename.split('.')[-1].lower() if '.' in filename else ''