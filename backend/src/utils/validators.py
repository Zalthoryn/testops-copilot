# backend/src/utils/validators.py
"""
Валидаторы для TestOps Copilot
"""
import re
import json
from typing import Dict, List, Any, Tuple, Optional
import yaml
from urllib.parse import urlparse

from src.utils.logger import get_logger

logger = get_logger(__name__)


def validate_requirements_text(text: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация текста требований.
    
    Args:
        text: Текст требований
    
    Returns:
        Tuple[валидно?, ошибка]
    """
    if not text or not text.strip():
        return False, "Текст требований не может быть пустым"
    
    if len(text.strip()) < 20:
        return False, "Текст требований слишком короткий (минимум 20 символов)"
    
    if len(text) > 10000:
        return False, "Текст требований слишком длинный (максимум 10000 символов)"
    
    return True, None


def validate_test_case_batch(testcases: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Валидация пакета тест-кейсов.
    
    Args:
        testcases: Список тест-кейсов
    
    Returns:
        Tuple[валидно?, ошибка]
    """
    if not testcases:
        return False, "Список тест-кейсов не может быть пустым"
    
    for i, testcase in enumerate(testcases):
        if not isinstance(testcase, dict):
            return False, f"Тест-кейс {i} должен быть словарем"
        
        # Проверяем обязательные поля
        if "title" not in testcase or not testcase["title"].strip():
            return False, f"Тест-кейс {i} не имеет заголовка"
        
        if "steps" not in testcase or not testcase["steps"]:
            return False, f"Тест-кейс {i} не имеет шагов"
        
        if not isinstance(testcase["steps"], list):
            return False, f"Шаги тест-кейса {i} должны быть списком"
        
        if "expected_result" not in testcase or not testcase["expected_result"].strip():
            return False, f"Тест-кейс {i} не имеет ожидаемого результата"
    
    return True, None


def validate_python_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Базовая валидация Python кода.
    
    Args:
        code: Python код
    
    Returns:
        Tuple[валидно?, ошибка]
    """
    if not code or not code.strip():
        return False, "Код не может быть пустым"
    
    # Проверяем наличие ключевых слов
    required_keywords = ["import", "def", "class"]
    for keyword in required_keywords:
        if keyword not in code:
            logger.warning(f"Generated code missing keyword: {keyword}")
    
    # Проверяем баланс скобок
    if code.count("(") != code.count(")"):
        return False, "Несбалансированные круглые скобки"
    
    if code.count("[") != code.count("]"):
        return False, "Несбалансированные квадратные скобки"
    
    if code.count("{") != code.count("}"):
        return False, "Несбалансированные фигурные скобки"
    
    return True, None


def validate_openapi_content(content: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация содержимого OpenAPI спецификации.
    
    Args:
        content: Содержимое OpenAPI
    
    Returns:
        Tuple[валидно?, ошибка]
    """
    if not content or not content.strip():
        return False, "Содержимое OpenAPI не может быть пустым"
    
    try:
        # Пытаемся загрузить как JSON
        try:
            spec = json.loads(content)
        except json.JSONDecodeError:
            # Пытаемся загрузить как YAML
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError:
                return False, "Неверный формат OpenAPI (ожидается JSON или YAML)"
        
        # Проверяем обязательные поля
        if not isinstance(spec, dict):
            return False, "OpenAPI спецификация должна быть объектом"
        
        if "openapi" not in spec:
            return False, "Отсутствует поле 'openapi'"
        
        if "info" not in spec:
            return False, "Отсутствует поле 'info'"
        
        if not isinstance(spec["info"], dict):
            return False, "Поле 'info' должно быть объектом"
        
        if "title" not in spec["info"]:
            return False, "Отсутствует поле 'title' в info"
        
        if "paths" not in spec:
            return False, "Отсутствует поле 'paths'"
        
        return True, None
        
    except Exception as e:
        return False, f"Ошибка валидации OpenAPI: {str(e)}"


def validate_url(url: str) -> bool:
    """
    Валидация URL.
    
    Args:
        url: URL для валидации
    
    Returns:
        True если URL валиден
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False


def validate_email(email: str) -> bool:
    """
    Валидация email адреса.
    
    Args:
        email: Email для валидации
    
    Returns:
        True если email валиден
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_uuid(uuid_str: str) -> bool:
    """
    Валидация UUID.
    
    Args:
        uuid_str: UUID строка
    
    Returns:
        True если UUID валиден
    """
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(pattern, uuid_str, re.IGNORECASE))


def validate_priority(priority: str) -> bool:
    """
    Валидация приоритета тест-кейса.
    
    Args:
        priority: Приоритет для валидации
    
    Returns:
        True если приоритет валиден
    """
    valid_priorities = {"CRITICAL", "NORMAL", "LOW", "P0", "P1", "P2", "P3"}
    return priority.upper() in valid_priorities


def validate_test_type(test_type: str) -> bool:
    """
    Валидация типа теста.
    
    Args:
        test_type: Тип теста для валидации
    
    Returns:
        True если тип теста валиден
    """
    valid_types = {"manual_ui", "manual_api", "auto_ui", "auto_api"}
    return test_type.lower() in valid_types


def sanitize_filename(filename: str) -> str:
    """
    Очистка имени файла от недопустимых символов.
    
    Args:
        filename: Исходное имя файла
    
    Returns:
        Очищенное имя файла
    """
    # Заменяем недопустимые символы на подчеркивания
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Удаляем лишние подчеркивания
    sanitized = re.sub(r'_+', '_', sanitized)
    # Удаляем подчеркивания в начале и конце
    sanitized = sanitized.strip('_')
    
    # Если имя файла стало пустым, возвращаем дефолтное
    if not sanitized:
        sanitized = "file"
    
    # Добавляем расширение если его нет
    if not sanitized.endswith('.py'):
        sanitized += '.py'
    
    return sanitized


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Валидация расширения файла.
    
    Args:
        filename: Имя файла
        allowed_extensions: Разрешенные расширения
    
    Returns:
        True если расширение разрешено
    """
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    return extension in [ext.lower() for ext in allowed_extensions]