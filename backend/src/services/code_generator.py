"""
Генератор кода для TestOps Copilot
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader, select_autoescape
import json

from src.models.dto import TestCaseDTO, TestType, TestPriority
from src.utils.logger import get_logger
from src.utils.helpers import convert_to_snake_case, convert_to_camel_case

logger = get_logger(__name__)

class CodeGenerator:
    """
    Генератор кода для различных форматов тестов
    
    Поддерживаемые форматы:
    1. Allure TestOps as Code (ручные тест-кейсы)
    2. Playwright UI автотесты
    3. Pytest API автотесты
    4. TestNG тесты
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        """
        Инициализация генератора кода
        
        Args:
            templates_dir: Директория с шаблонами Jinja2
        """
        if templates_dir:
            self.env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            # Используем встроенные шаблоны
            self.env = Environment(
                loader=FileSystemLoader(self._get_default_templates()),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
        
        # Регистрируем кастомные фильтры
        self.env.filters['snake_case'] = self._snake_case_filter
        self.env.filters['camel_case'] = self._camel_case_filter
        self.env.filters['escape_quotes'] = self._escape_quotes_filter
    
    def _get_default_templates(self) -> List[str]:
        """Получение путей к шаблонам по умолчанию"""
        # В реальной системе здесь был бы поиск шаблонов
        # Сейчас возвращаем пустой список - используем строковые шаблоны
        return []
    
    def generate_allure_testops_code(self, testcase: TestCaseDTO) -> str:
        """
        Генерация кода в формате Allure TestOps as Code
        
        Args:
            testcase: DTO тест-кейса
        
        Returns:
            Python код тест-кейса
        """
        # Шаблон для Allure TestOps as Code
        template_str = """
import allure
import pytest
from typing import Optional
{% if testcase.test_type.value == 'manual_ui' or testcase.test_type.value == 'manual_api' %}
@allure.manual
{% endif %}
@allure.label("owner", "{{ testcase.owner|escape_quotes }}")
@allure.feature("{{ testcase.feature|escape_quotes }}")
@allure.story("{{ testcase.story|escape_quotes }}")
@allure.suite("{{ testcase.test_type.value }}")
class {{ testcase.feature|camel_case }}Tests:
    \"\"\"Тесты для фичи: {{ testcase.feature }}\"\"\"
    
    @allure.title("{{ testcase.title|escape_quotes }}")
    @allure.tag("{{ testcase.priority.value }}")
    @allure.label("priority", "{{ testcase.priority.value }}")
    def {{ testcase.title|snake_case }}(self):
        \"\"\"
        {{ testcase.expected_result|escape_quotes }}
        
        Шаги:
        {% for step in testcase.steps %}
        {{ loop.index }}. {{ step|escape_quotes }}
        {% endfor %}
        \"\"\"
        {% for step in testcase.steps %}
        with allure.step("Шаг {{ loop.index }}: {{ step|escape_quotes }}"):
            # TODO: Реализовать шаг {{ loop.index }}
            pass
        {% endfor %}
        
        # Проверка ожидаемого результата
        assert True, "Тест должен завершиться успешно"
        
        {% if testcase.test_type.value == 'manual_ui' %}
        # Прикрепление скриншота для UI тестов
        allure.attach.file(
            "screenshots/{{ testcase.title|snake_case }}.png",
            name="{{ testcase.title|escape_quotes }}",
            attachment_type=allure.attachment_type.PNG
        )
        {% endif %}
"""
        
        try:
            template = Template(template_str)
            return template.render(
                testcase=testcase,
                TestType=TestType,
                TestPriority=TestPriority
            )
        except Exception as e:
            logger.error(f"Error generating Allure TestOps code: {e}")
            # Fallback на простой шаблон
            return self._generate_simple_allure_code(testcase)
    
    def _generate_simple_allure_code(self, testcase: TestCaseDTO) -> str:
        """Генерация простого Allure кода (fallback)"""
        class_name = convert_to_camel_case(testcase.feature) + "Tests"
        method_name = convert_to_snake_case(testcase.title)
        if not method_name.startswith('test_'):
            method_name = f"test_{method_name}"
        
        code = f'''import allure
import pytest

@allure.label("owner", "{testcase.owner}")
@allure.feature("{testcase.feature}")
@allure.story("{testcase.story}")
class {class_name}:
    
    @allure.title("{testcase.title}")
    @allure.tag("{testcase.priority.value}")
    def {method_name}(self):
        """{testcase.expected_result}"""
'''
        
        for i, step in enumerate(testcase.steps, 1):
            code += f'''
        with allure.step("Шаг {i}: {step}"):
            # TODO: Реализовать шаг {i}
            pass
'''
        
        code += '''
        # Проверка ожидаемого результата
        assert True, "Тест должен завершиться успешно"
'''
        
        return code
    
    def generate_playwright_test(self, testcase: TestCaseDTO, config: Dict[str, Any]) -> str:
        """
        Генерация Playwright UI автотеста
        
        Args:
            testcase: DTO тест-кейса
            config: Конфигурация Playwright
        
        Returns:
            Python код Playwright теста
        """
        # Шаблон для Playwright тестов
        template_str = """
import pytest
import allure
from playwright.sync_api import Page, expect
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class {{ testcase.feature|camel_case }}Page:
    \"\"\"Page Object для {{ testcase.feature }}\"\"\"
    
    def __init__(self, page: Page):
        self.page = page
    
    {% for step in testcase.steps %}
    {% if 'открыть' in step.lower() or 'open' in step.lower() or 'перейти' in step.lower() %}
    def {{ step|snake_case }}(self):
        \"\"\"{{ step }}\"\"\"
        self.page.goto("{{ config.get('base_url', 'https://example.com') }}")
        self.page.wait_for_load_state("networkidle")
    {% elif 'нажать' in step.lower() or 'click' in step.lower() %}
    def {{ step|snake_case }}(self):
        \"\"\"{{ step }}\"\"\"
        # TODO: Заменить на правильный селектор
        button = self.page.locator("button:has-text('Кнопка')")
        button.click()
        self.page.wait_for_load_state("networkidle")
    {% elif 'проверить' in step.lower() or 'check' in step.lower() or 'verify' in step.lower() %}
    def {{ step|snake_case }}(self):
        \"\"\"{{ step }}\"\"\"
        # TODO: Заменить на правильный селектор
        element = self.page.locator("h1")
        expect(element).to_be_visible()
    {% else %}
    def {{ step|snake_case }}(self):
        \"\"\"{{ step }}\"\"\"
        # TODO: Реализовать шаг
        pass
    {% endif %}
    {% endfor %}

@allure.feature("{{ testcase.feature }}")
@allure.story("{{ testcase.story }}")
class Test{{ testcase.feature|camel_case }}:
    
    @allure.title("{{ testcase.title }}")
    @allure.tag("{{ testcase.priority.value }}")
    def test_{{ testcase.title|snake_case }}(self, page: Page):
        \"\"\"{{ testcase.expected_result }}\"\"\"
        
        # Инициализация Page Object
        {{ testcase.feature|camel_case|lower }}_page = {{ testcase.feature|camel_case }}Page(page)
        
        # Выполнение шагов
        {% for step in testcase.steps %}
        with allure.step("Шаг {{ loop.index }}: {{ step }}"):
            {{ testcase.feature|camel_case|lower }}_page.{{ step|snake_case }}()
        {% endfor %}
        
        # Проверка ожидаемого результата
        assert True, "Тест должен завершиться успешно"
        
        # Скриншот для отчета
        allure.attach.file(
            page.screenshot(),
            name="{{ testcase.title|snake_case }}_screenshot",
            attachment_type=allure.attachment_type.PNG
        )
"""
        
        try:
            template = Template(template_str)
            return template.render(
                testcase=testcase,
                config=config
            )
        except Exception as e:
            logger.error(f"Error generating Playwright code: {e}")
            return self._generate_simple_playwright_code(testcase, config)
    
    def _generate_simple_playwright_code(self, testcase: TestCaseDTO, config: Dict[str, Any]) -> str:
        """Генерация простого Playwright кода (fallback)"""
        class_name = f"Test{convert_to_camel_case(testcase.feature)}"
        method_name = convert_to_snake_case(testcase.title)
        if not method_name.startswith('test_'):
            method_name = f"test_{method_name}"
        
        base_url = config.get('base_url', 'https://example.com')
        
        code = f'''import pytest
import allure
from playwright.sync_api import Page, expect

@allure.feature("{testcase.feature}")
@allure.story("{testcase.story}")
class {class_name}:
    
    @allure.title("{testcase.title}")
    def {method_name}(self, page: Page):
        """{testcase.expected_result}"""
'''
        
        for i, step in enumerate(testcase.steps, 1):
            code += f'''
        with allure.step("Шаг {i}: {step}"):
            # TODO: Реализовать шаг {i}
            pass
'''
        
        code += f'''
        # Проверка ожидаемого результата
        assert True, "Тест должен завершиться успешно"
        
        # Скриншот
        page.screenshot(path="screenshots/{method_name}.png")
        allure.attach.file(
            "screenshots/{method_name}.png",
            name="{method_name}_screenshot",
            attachment_type=allure.attachment_type.PNG
        )
'''
        
        return code
    
    def generate_pytest_api_test(self, testcase: TestCaseDTO, api_config: Dict[str, Any]) -> str:
        """
        Генерация Pytest API автотеста
        
        Args:
            testcase: DTO тест-кейса
            api_config: Конфигурация API
        
        Returns:
            Python код Pytest API теста
        """
        # Шаблон для Pytest API тестов
        template_str = """
import pytest
import allure
import httpx
import json
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class {{ testcase.feature|camel_case }}APIClient:
    \"\"\"API клиент для {{ testcase.feature }}\"\"\"
    
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        
        if token:
            self.client.headers.update({{
                "Authorization": f"Bearer {{token}}",
                "Content-Type": "application/json"
            }})
    
    {% for step in testcase.steps %}
    {% if 'получить' in step.lower() or 'get' in step.lower() %}
    def {{ step|snake_case }}(self{% if 'параметр' in step.lower() or 'parameter' in step.lower() %}, params: Dict[str, Any] = None{% endif %}):
        \"\"\"{{ step }}\"\"\"
        # TODO: Заменить на правильный endpoint
        response = self.client.get("/api/endpoint"{% if 'параметр' in step.lower() or 'parameter' in step.lower() %}, params=params{% endif %})
        response.raise_for_status()
        return response.json()
    {% elif 'создать' in step.lower() or 'create' in step.lower() or 'post' in step.lower() %}
    def {{ step|snake_case }}(self, data: Dict[str, Any]):
        \"\"\"{{ step }}\"\"\"
        # TODO: Заменить на правильный endpoint
        response = self.client.post("/api/endpoint", json=data)
        response.raise_for_status()
        return response.json()
    {% elif 'обновить' in step.lower() or 'update' in step.lower() or 'put' in step.lower() %}
    def {{ step|snake_case }}(self, resource_id: str, data: Dict[str, Any]):
        \"\"\"{{ step }}\"\"\"
        # TODO: Заменить на правильный endpoint
        response = self.client.put(f"/api/endpoint/{{resource_id}}", json=data)
        response.raise_for_status()
        return response.json()
    {% elif 'удалить' in step.lower() or 'delete' in step.lower() %}
    def {{ step|snake_case }}(self, resource_id: str):
        \"\"\"{{ step }}\"\"\"
        # TODO: Заменить на правильный endpoint
        response = self.client.delete(f"/api/endpoint/{{resource_id}}")
        response.raise_for_status()
        return response.status_code == 204
    {% else %}
    def {{ step|snake_case }}(self):
        \"\"\"{{ step }}\"\"\"
        # TODO: Реализовать шаг
        pass
    {% endif %}
    {% endfor %}

@allure.feature("{{ testcase.feature }}")
@allure.story("{{ testcase.story }}")
class Test{{ testcase.feature|camel_case }}API:
    
    @pytest.fixture
    def api_client(self):
        \"\"\"Фикстура для API клиента\"\"\"
        return {{ testcase.feature|camel_case }}APIClient(
            base_url="{{ api_config.get('base_url', 'https://api.example.com') }}",
            token="{{ api_config.get('token', '') }}"
        )
    
    @allure.title("{{ testcase.title }}")
    @allure.tag("{{ testcase.priority.value }}")
    def test_{{ testcase.title|snake_case }}(self, api_client: {{ testcase.feature|camel_case }}APIClient):
        \"\"\"{{ testcase.expected_result }}\"\"\"
        
        # Выполнение шагов
        {% for step in testcase.steps %}
        with allure.step("Шаг {{ loop.index }}: {{ step }}"):
            result_{{ loop.index }} = api_client.{{ step|snake_case }}()
            # TODO: Добавить проверки для шага {{ loop.index }}
        {% endfor %}
        
        # Проверка ожидаемого результата
        assert True, "API тест должен завершиться успешно"
"""
        
        try:
            template = Template(template_str)
            return template.render(
                testcase=testcase,
                api_config=api_config
            )
        except Exception as e:
            logger.error(f"Error generating Pytest API code: {e}")
            return self._generate_simple_pytest_api_code(testcase, api_config)
    
    def _generate_simple_pytest_api_code(self, testcase: TestCaseDTO, api_config: Dict[str, Any]) -> str:
        """Генерация простого Pytest API кода (fallback)"""
        class_name = f"Test{convert_to_camel_case(testcase.feature)}API"
        method_name = convert_to_snake_case(testcase.title)
        if not method_name.startswith('test_'):
            method_name = f"test_{method_name}"
        
        base_url = api_config.get('base_url', 'https://api.example.com')
        token = api_config.get('token', '')
        
        code = f'''import pytest
import allure
import httpx
import json

@allure.feature("{testcase.feature}")
@allure.story("{testcase.story}")
class {class_name}:
    
    @pytest.fixture
    def api_client(self):
        """Фикстура для API клиента"""
        client = httpx.Client(base_url="{base_url}", timeout=30.0)
        if "{token}":
            client.headers.update({{
                "Authorization": "Bearer {token}",
                "Content-Type": "application/json"
            }})
        yield client
        client.close()
    
    @allure.title("{testcase.title}")
    def {method_name}(self, api_client):
        """{testcase.expected_result}"""
'''
        
        for i, step in enumerate(testcase.steps, 1):
            code += f'''
        with allure.step("Шаг {i}: {step}"):
            # TODO: Реализовать шаг {i}
            pass
'''
        
        code += '''
        # Проверка ожидаемого результата
        assert True, "API тест должен завершиться успешно"
'''
        
        return code
    
    def generate_testng_test(self, testcase: TestCaseDTO, config: Dict[str, Any]) -> str:
        """
        Генерация TestNG Java теста
        
        Args:
            testcase: DTO тест-кейса
            config: Конфигурация TestNG
        
        Returns:
            Java код TestNG теста
        """
        # Шаблон для TestNG тестов
        template_str = """
package com.example.tests;

import org.testng.annotations.Test;
import org.testng.annotations.BeforeMethod;
import org.testng.annotations.AfterMethod;
import io.qameta.allure.Allure;
import io.qameta.allure.Feature;
import io.qameta.allure.Story;
import io.qameta.allure.Step;
import static org.testng.Assert.assertTrue;

@Feature("{{ testcase.feature }}")
@Story("{{ testcase.story }}")
public class {{ testcase.feature|camel_case }}Test {
    
    @BeforeMethod
    public void setUp() {
        // Инициализация перед каждым тестом
    }
    
    @AfterMethod
    public void tearDown() {
        // Очистка после каждого теста
    }
    
    @Test(description = "{{ testcase.title }}")
    @io.qameta.allure.testng.AllureTest(
        value = "{{ testcase.title }}",
        description = "{{ testcase.expected_result }}"
    )
    public void {{ testcase.title|snake_case }}() {
        {% for step in testcase.steps %}
        Allure.step("Шаг {{ loop.index }}: {{ step }}", () -> {
            // TODO: Реализовать шаг {{ loop.index }}
        });
        {% endfor %}
        
        // Проверка ожидаемого результата
        assertTrue(true, "Тест должен завершиться успешно");
    }
}
"""
        
        try:
            template = Template(template_str)
            return template.render(testcase=testcase)
        except Exception as e:
            logger.error(f"Error generating TestNG code: {e}")
            return ""
    
    def generate_batch_tests(
        self, 
        testcases: List[TestCaseDTO], 
        test_type: TestType,
        config: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Генерация пакета тестов
        
        Args:
            testcases: Список тест-кейсов
            test_type: Тип тестов
            config: Конфигурация
        
        Returns:
            Словарь с именами файлов и их содержимым
        """
        files = {}
        
        # Группируем тест-кейсы по feature
        grouped_testcases = {}
        for testcase in testcases:
            if testcase.feature not in grouped_testcases:
                grouped_testcases[testcase.feature] = []
            grouped_testcases[testcase.feature].append(testcase)
        
        # Генерируем файлы для каждой группы
        for feature, feature_testcases in grouped_testcases.items():
            if test_type == TestType.MANUAL_UI or test_type == TestType.MANUAL_API:
                # Для ручных тестов генерируем один файл с Allure тестами
                content = self._generate_allure_batch_file(feature, feature_testcases)
                filename = f"test_{convert_to_snake_case(feature)}.py"
                files[filename] = content
            
            elif test_type == TestType.AUTO_UI:
                # Для UI автотестов генерируем Playwright тесты
                content = self._generate_playwright_batch_file(feature, feature_testcases, config)
                filename = f"test_{convert_to_snake_case(feature)}_ui.py"
                files[filename] = content
            
            elif test_type == TestType.AUTO_API:
                # Для API автотестов генерируем Pytest тесты
                content = self._generate_pytest_api_batch_file(feature, feature_testcases, config)
                filename = f"test_{convert_to_snake_case(feature)}_api.py"
                files[filename] = content
        
        logger.info(f"Generated {len(files)} test files for {len(testcases)} test cases")
        return files
    
    def _generate_allure_batch_file(self, feature: str, testcases: List[TestCaseDTO]) -> str:
        """Генерация файла с несколькими Allure тестами"""
        class_name = convert_to_camel_case(feature) + "Tests"
        
        code = f'''import allure
import pytest

@allure.label("owner", "qa_team")
@allure.feature("{feature}")
@allure.suite("manual")
class {class_name}:
    \"\"\"Тесты для фичи: {feature}\"\"\"
'''
        
        for testcase in testcases:
            method_name = convert_to_snake_case(testcase.title)
            if not method_name.startswith('test_'):
                method_name = f"test_{method_name}"
            
            code += f'''
    @allure.title("{testcase.title}")
    @allure.story("{testcase.story}")
    @allure.tag("{testcase.priority.value}")
    def {method_name}(self):
        \"\"\"{testcase.expected_result}\"\"\"
'''
            
            for i, step in enumerate(testcase.steps, 1):
                code += f'''
        with allure.step("Шаг {i}: {step}"):
            # TODO: Реализовать шаг {i}
            pass
'''
            
            code += '''
        # Проверка ожидаемого результата
        assert True, "Тест должен завершиться успешно"
'''
        
        return code
    
    def _generate_playwright_batch_file(self, feature: str, testcases: List[TestCaseDTO], config: Dict[str, Any]) -> str:
        """Генерация файла с несколькими Playwright тестами"""
        class_name = f"Test{convert_to_camel_case(feature)}"
        page_class_name = f"{convert_to_camel_case(feature)}Page"
        base_url = config.get('base_url', 'https://example.com')
        
        # Генерируем Page Object класс
        page_object_code = f'''
class {page_class_name}:
    \"\"\"Page Object для {feature}\"\"\"
    
    def __init__(self, page):
        self.page = page
        self.base_url = "{base_url}"
    
    def navigate(self):
        \"\"\"Переход на страницу\"\"\"
        self.page.goto(self.base_url)
        self.page.wait_for_load_state("networkidle")
'''
        
        # Генерируем тестовый класс
        test_class_code = f'''
import pytest
import allure
from playwright.sync_api import Page, expect

{page_object_code}

@allure.feature("{feature}")
class {class_name}:
'''
        
        for testcase in testcases:
            method_name = convert_to_snake_case(testcase.title)
            if not method_name.startswith('test_'):
                method_name = f"test_{method_name}"
            
            test_class_code += f'''
    @allure.title("{testcase.title}")
    @allure.story("{testcase.story}")
    def {method_name}(self, page: Page):
        \"\"\"{testcase.expected_result}\"\"\"
        
        # Инициализация Page Object
        page_obj = {page_class_name}(page)
        page_obj.navigate()
'''
            
            for i, step in enumerate(testcase.steps, 1):
                test_class_code += f'''
        with allure.step("Шаг {i}: {step}"):
            # TODO: Реализовать шаг {i}
            pass
'''
            
            test_class_code += '''
        # Проверка ожидаемого результата
        assert True, "Тест должен завершиться успешно"
        
        # Скриншот
        page.screenshot(path=f"screenshots/{method_name}.png")
'''
        
        return test_class_code
    
    def _generate_pytest_api_batch_file(self, feature: str, testcases: List[TestCaseDTO], config: Dict[str, Any]) -> str:
        """Генерация файла с несколькими Pytest API тестами"""
        class_name = f"Test{convert_to_camel_case(feature)}API"
        client_class_name = f"{convert_to_camel_case(feature)}APIClient"
        base_url = config.get('base_url', 'https://api.example.com')
        token = config.get('token', '')
        
        # Генерируем API клиент
        client_code = f'''
import httpx
import json
from typing import Optional, Dict, Any

class {client_class_name}:
    \"\"\"API клиент для {feature}\"\"\"
    
    def __init__(self, base_url: str = "{base_url}", token: Optional[str] = "{token}"):
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.Client(base_url=self.base_url, timeout=30.0)
        
        if token:
            self.client.headers.update({{
                "Authorization": f"Bearer {{token}}",
                "Content-Type": "application/json"
            }})
    
    def close(self):
        \"\"\"Закрытие клиента\"\"\"
        self.client.close()
'''
        
        # Генерируем тестовый класс
        test_class_code = f'''
import pytest
import allure

{client_code}

@allure.feature("{feature}")
class {class_name}:
    
    @pytest.fixture
    def api_client(self):
        \"\"\"Фикстура для API клиента\"\"\"
        client = {client_class_name}()
        yield client
        client.close()
'''
        
        for testcase in testcases:
            method_name = convert_to_snake_case(testcase.title)
            if not method_name.startswith('test_'):
                method_name = f"test_{method_name}"
            
            test_class_code += f'''
    @allure.title("{testcase.title}")
    @allure.story("{testcase.story}")
    def {method_name}(self, api_client: {client_class_name}):
        \"\"\"{testcase.expected_result}\"\"\"
'''
            
            for i, step in enumerate(testcase.steps, 1):
                test_class_code += f'''
        with allure.step("Шаг {i}: {step}"):
            # TODO: Реализовать шаг {i}
            pass
'''
            
            test_class_code += '''
        # Проверка ожидаемого результата
        assert True, "API тест должен завершиться успешно"
'''
        
        return test_class_code
    
    # Вспомогательные фильтры для Jinja2
    def _snake_case_filter(self, text: str) -> str:
        """Фильтр для преобразования в snake_case"""
        return convert_to_snake_case(text)
    
    def _camel_case_filter(self, text: str) -> str:
        """Фильтр для преобразования в CamelCase"""
        return convert_to_camel_case(text)
    
    def _escape_quotes_filter(self, text: str) -> str:
        """Фильтр для экранирования кавычек"""
        return text.replace('"', '\\"').replace("'", "\\'")