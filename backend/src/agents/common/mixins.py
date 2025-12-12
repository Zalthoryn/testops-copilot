"""
Миксины для общих функций агентов
"""
from typing import List, Dict, Any, Optional
import re
import json
from uuid import UUID

from ...models.dto import TestCaseDTO, TestType, TestPriority
from ...utils.logger import get_logger

logger = get_logger(__name__)


class TestCaseProcessingMixin:
    """Миксин для обработки тест-кейсов"""
    
    def _format_testcases_for_prompt(self, testcases: List[TestCaseDTO]) -> str:
        """Форматирование тест-кейсов для промпта"""
        formatted = []
        
        for i, testcase in enumerate(testcases, 1):
            formatted.append(f"""
            ТЕСТ-КЕЙС {i}: {testcase.title}
            - Приоритет: {testcase.priority.value}
            - Feature: {testcase.feature}
            - Story: {testcase.story}
            - Тип теста: {testcase.test_type.value}
            - Шаги:
            {chr(10).join(f'    {j+1}. {step}' for j, step in enumerate(testcase.steps))}
            - Ожидаемый результат: {testcase.expected_result}
            """)
        
        return "\n".join(formatted)
    
    def _group_testcases_by_feature(self, testcases: List[TestCaseDTO]) -> Dict[str, List[TestCaseDTO]]:
        """Группировка тест-кейсов по feature"""
        grouped = {}
        
        for testcase in testcases:
            feature = testcase.feature
            if feature not in grouped:
                grouped[feature] = []
            grouped[feature].append(testcase)
        
        logger.debug(f"Grouped {len(testcases)} test cases into {len(grouped)} features")
        return grouped
    
    def _extract_testcases_from_response(self, parsed_response: Dict) -> List[Dict]:
        """
        Извлечение тест-кейсов из ответа LLM в различных форматах
        """
        testcases = []
        
        # Пытаемся найти тест-кейсы в разных форматах
        possible_keys = ["testcases", "test_cases", "testCases", "tests", "cases"]
        
        for key in possible_keys:
            if key in parsed_response and isinstance(parsed_response[key], list):
                testcases = parsed_response[key]
                break
        
        # Если не нашли в явном виде, ищем в корне ответа
        if not testcases and isinstance(parsed_response, list):
            testcases = parsed_response
        elif not testcases:
            # Пытаемся извлечь из текстового ответа
            testcases = self._extract_testcases_from_text(json.dumps(parsed_response))
        
        return testcases
    
    def _extract_testcases_from_text(self, text: str) -> List[Dict]:
        """Извлечение тест-кейсов из текстового ответа"""
        testcases = []
        
        # Пытаемся найти JSON блоки в тексте
        json_patterns = [
            r'```json\s*(.*?)\s*```',  # ```json ... ```
            r'```\s*(.*?)\s*```',      # ``` ... ```
            r'\[.*\]',                  # Массив JSON
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        testcases.extend(data)
                    elif isinstance(data, dict) and "testcases" in data:
                        testcases.extend(data["testcases"])
                except json.JSONDecodeError:
                    continue
        
        return testcases
    
    def _detect_story_from_content(self, testcase_data: Dict, available_stories: List[str]) -> str:
        """Определение story тест-кейса по его содержанию"""
        title = testcase_data.get("title", "").lower()
        steps = testcase_data.get("steps", [])
        steps_text = " ".join([str(s).lower() for s in steps])
        
        # Простая логика определения story по ключевым словам
        if "api" in title or any("api" in str(s).lower() for s in steps):
            return "API Testing"
        elif "ui" in title or any("ui" in str(s).lower() for s in steps):
            return "UI Testing"
        elif "mobile" in title or any("mobile" in str(s).lower() for s in steps):
            return "Mobile Testing"
        
        # Возвращаем первую доступную story или общую
        return available_stories[0] if available_stories else "General Testing"


class CodeGenerationMixin:
    """Миксин для генерации кода"""
    
    def _parse_llm_response_for_code(self, response: str) -> str:
        """Парсинг ответа LLM для извлечения кода"""
        code_patterns = [
            r'```python\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                return matches[0].strip()
        
        return response.strip()
    
    def _generate_filename(self, name: str, prefix: str = "test") -> str:
        """Генерация имени файла"""
        import re
        
        # Очищаем название
        clean_name = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower())
        clean_name = re.sub(r'_+', '_', clean_name).strip('_')
        
        return f"{prefix}_{clean_name}.py"
    
    def _validate_generated_code(self, code: str) -> bool:
        """Базовая валидация сгенерированного кода"""
        # Проверяем наличие обязательных ключевых слов
        required_keywords = ["import", "def", "class", "test"]
        
        for keyword in required_keywords:
            if keyword not in code:
                logger.warning(f"Generated code missing required keyword: {keyword}")
                return False
        
        # Проверяем синтаксис (базовая проверка)
        try:
            if code.count("(") != code.count(")"):
                logger.warning("Mismatched parentheses in generated code")
                return False
            
            if code.count("[") != code.count("]"):
                logger.warning("Mismatched brackets in generated code")
                return False
            
            if code.count("{") != code.count("}"):
                logger.warning("Mismatched braces in generated code")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Code validation error: {e}")
            return False


class OpenAPIMixin:
    """Миксин для работы с OpenAPI"""
    
    def _extract_base_url(self, openapi_spec: Dict) -> str:
        """Извлечение базового URL из OpenAPI спецификации"""
        servers = openapi_spec.get("servers", [])
        if servers:
            server_url = servers[0].get("url", "")
            if "{" in server_url:
                server_url = re.sub(r'\{.*?\}', 'example', server_url)
            return server_url
        return "https://api.example.com"
    
    def _extract_auth_info(self, openapi_spec: Dict) -> Dict:
        """Извлечение информации об аутентификации"""
        auth_info = {
            "type": "none",
            "schemes": []
        }
        
        security_schemes = openapi_spec.get("components", {}).get("securitySchemes", {})
        
        for scheme_name, scheme_def in security_schemes.items():
            scheme_type = scheme_def.get("type", "")
            if scheme_type == "http":
                auth_info["type"] = "bearer"
                auth_info["schemes"].append({
                    "name": scheme_name,
                    "type": scheme_type,
                    "scheme": scheme_def.get("scheme", "bearer")
                })
            elif scheme_type == "apiKey":
                auth_info["type"] = "apiKey"
                auth_info["schemes"].append({
                    "name": scheme_name,
                    "type": scheme_type,
                    "in": scheme_def.get("in", "header"),
                    "name": scheme_def.get("name", "api_key")
                })
        
        return auth_info
    
    def _extract_all_endpoints(self, openapi_spec: Dict) -> List[Dict]:
        """Извлечение всех endpoints из OpenAPI спецификации"""
        endpoints = []
        paths = openapi_spec.get("paths", {})
        
        for path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue
                
            for method, details in path_item.items():
                method_lower = method.lower()
                if method_lower in ["get", "post", "put", "patch", "delete", "head", "options"]:
                    if not isinstance(details, dict):
                        continue
                        
                    endpoint = {
                        "path": path,
                        "method": method.upper(),
                        "operation_id": details.get("operationId", ""),
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "parameters": details.get("parameters", []),
                        "request_body": details.get("requestBody"),
                        "responses": details.get("responses", {}),
                        "tags": details.get("tags", [])
                    }
                    endpoints.append(endpoint)
        
        return endpoints
    
    def _format_endpoints_for_prompt(self, endpoints: List[Dict], limit: int = 20) -> str:
        """Форматирование endpoints для промпта"""
        if not endpoints:
            return "Нет endpoints для тестирования"
        
        formatted = []
        for i, endpoint in enumerate(endpoints[:limit]):
            formatted.append(f"""
            ENDPOINT {i+1}: {endpoint['method']} {endpoint['path']}
            - ID операции: {endpoint.get('operation_id', 'N/A')}
            - Описание: {endpoint.get('summary', endpoint.get('description', 'Нет описания'))}
            - Параметры: {len(endpoint.get('parameters', []))}
            - Теги: {', '.join(endpoint.get('tags', []))}
            """)
        
        if len(endpoints) > limit:
            formatted.append(f"\n... и еще {len(endpoints) - limit} endpoints")
        
        return "\n".join(formatted)