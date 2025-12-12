"""
Парсер OpenAPI спецификаций для TestOps Copilot
"""
import json
import yaml
from typing import Dict, Any, Optional
import httpx
from ..utils.logger import get_logger
from ..utils.exceptions import OpenAPIException

logger = get_logger(__name__)

class OpenAPIParser:
    """Парсер OpenAPI спецификаций"""
    
    async def parse_from_url(self, url: str) -> Dict[str, Any]:
        """Загрузка и парсинг OpenAPI из URL"""
        try:
            logger.info(f"Загрузка OpenAPI из URL: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
                
                content_type = response.headers.get('content-type', '')
                
                if 'application/json' in content_type:
                    return response.json()
                elif 'application/yaml' in content_type or 'text/yaml' in content_type:
                    return yaml.safe_load(response.text)
                else:
                    # Пробуем определить формат по содержимому
                    try:
                        return response.json()
                    except:
                        return yaml.safe_load(response.text)
                        
        except Exception as e:
            logger.error(f"Ошибка загрузки OpenAPI из URL: {e}")
            raise OpenAPIException(f"Не удалось загрузить OpenAPI спецификацию: {str(e)}")
    
    def parse_from_content(self, content: str) -> Dict[str, Any]:
        """Парсинг OpenAPI из строки содержимого"""
        try:
            # Пробуем JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Пробуем YAML
                return yaml.safe_load(content)
                
        except Exception as e:
            logger.error(f"Ошибка парсинга OpenAPI: {e}")
            raise OpenAPIException(f"Не удалось распарсить OpenAPI спецификацию: {str(e)}")
    
    def filter_by_tags(self, spec: Dict[str, Any], tags: list) -> Dict[str, Any]:
        """Фильтрация спецификации по тегам"""
        filtered_paths = {}
        
        for path, methods in spec.get('paths', {}).items():
            for method, definition in methods.items():
                method_tags = definition.get('tags', [])
                if any(tag in tags for tag in method_tags):
                    if path not in filtered_paths:
                        filtered_paths[path] = {}
                    filtered_paths[path][method] = definition
        
        filtered_spec = spec.copy()
        filtered_spec['paths'] = filtered_paths
        
        logger.info(f"Отфильтровано {len(filtered_paths)} эндпоинтов по тегам: {tags}")
        return filtered_spec
    
    def get_endpoints_summary(self, spec: Dict[str, Any]) -> list:
        """Получение краткого описания эндпоинтов"""
        endpoints = []
        
        for path, methods in spec.get('paths', {}).items():
            for method, definition in methods.items():
                endpoints.append({
                    'method': method.upper(),
                    'path': path,
                    'summary': definition.get('summary', ''),
                    'tags': definition.get('tags', []),
                    'operationId': definition.get('operationId', '')
                })
        
        return endpoints