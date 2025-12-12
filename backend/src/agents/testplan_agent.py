"""
Агент для генерации тест-планов на основе анализа покрытия
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from enum import Enum
import json

from .base_agent import BaseAgent, AgentResult
from ..models.dto import TestCaseDTO, TestPriority
from ..services.llm_client import LLMClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

class TestPlanType(str, Enum):
    """Типы тест-планов"""
    REGRESSION = "regression"
    SMOKE = "smoke"
    SANITY = "sanity"
    FULL = "full"
    RELEASE = "release"

class TestPlanInput(BaseModel):
    """Входные данные для генерации тест-плана"""
    job_id: UUID
    testcases: List[TestCaseDTO] = Field(..., description="Тест-кейсы для включения в план")
    requirements: Optional[str] = Field(None, description="Текст требований")
    plan_type: TestPlanType = Field(default=TestPlanType.REGRESSION, 
                                   description="Тип тест-плана")
    priority_filter: Optional[List[TestPriority]] = Field(
        default=None,
        description="Фильтр по приоритету"
    )
    target_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.5, le=40,
        description="Целевая длительность выполнения в часах"
    )
    
    class Config:
        json_schema_extra  = {
            "example": {
                "job_id": "123e4567-e89b-12d3-a456-426614174000",
                "testcases": [],
                "requirements": "Основные требования к релизу",
                "plan_type": "regression",
                "priority_filter": ["CRITICAL", "NORMAL"],
                "target_duration_hours": 8.0
            }
        }

class TestPlanPhase(BaseModel):
    """Фаза тест-плана"""
    name: str
    description: str
    duration_hours: float
    testcases: List[UUID]
    objectives: List[str]
    entry_criteria: List[str]
    exit_criteria: List[str]

class TestPlanResource(BaseModel):
    """Ресурс для выполнения тест-плана"""
    role: str
    count: int
    skills: List[str]
    responsibilities: List[str]

class TestPlanOutput(AgentResult):
    """Результат генерации тест-плана"""
    test_plan: Dict[str, Any] = {}
    phases: List[TestPlanPhase] = []
    resources: List[TestPlanResource] = []
    schedule: Dict[str, Any] = {}
    risk_assessment: Dict[str, Any] = {}

class TestPlan_Agent(BaseAgent):
    """Агент для генерации тест-планов"""
    
    def __init__(self, llm_client: LLMClient, **kwargs):
        super().__init__(llm_client, **kwargs)
        self.plan_templates = self._load_plan_templates()
    
    async def execute(self, input_data: TestPlanInput) -> TestPlanOutput:
        """Генерация тест-плана"""
        self.logger.info(f"Запуск генерации тест-плана типа {input_data.plan_type} для job: {input_data.job_id}")
        
        try:
            # Фильтрация тест-кейсов
            filtered_testcases = self._filter_testcases(
                input_data.testcases, 
                input_data.priority_filter
            )
            
            if not filtered_testcases:
                raise ValueError("Нет тест-кейсов для включения в тест-план")
            
            # Анализ тест-кейсов
            testcase_analysis = self._analyze_testcases(filtered_testcases)
            
            # Подготовка промпта для LLM
            prompt = self._build_prompt(
                filtered_testcases, 
                testcase_analysis, 
                input_data
            )
            
            # Вызов LLM
            self.logger.info("Вызов LLM для генерации тест-плана")
            llm_response, exec_time = await self._measure_execution_time(
                self._call_llm, prompt, temperature=0.4, max_tokens=3000
            )
            
            # Парсинг ответа LLM
            test_plan_data = self._parse_llm_response(llm_response)
            
            # Дополнение данными из анализа
            enriched_plan = self._enrich_plan_with_analysis(
                test_plan_data, 
                testcase_analysis, 
                input_data
            )
            
            # Создание объектов фаз и ресурсов
            phases = self._create_phases(enriched_plan.get("phases", []), filtered_testcases)
            resources = self._create_resources(enriched_plan.get("resources", []))
            
            return TestPlanOutput(
                success=True,
                test_plan=enriched_plan,
                phases=phases,
                resources=resources,
                schedule=enriched_plan.get("schedule", {}),
                risk_assessment=enriched_plan.get("risk_assessment", {}),
                execution_time=exec_time,
                metrics={
                    "total_testcases": len(filtered_testcases),
                    "plan_type": input_data.plan_type.value,
                    "estimated_duration_hours": enriched_plan.get("total_duration_hours", 0),
                    "phases_count": len(phases)
                }
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации тест-плана: {e}")
            return TestPlanOutput(
                success=False,
                error=str(e),
                test_plan={},
                phases=[],
                resources=[]
            )
    
    def _filter_testcases(self, testcases: List[TestCaseDTO], 
                         priority_filter: Optional[List[TestPriority]]) -> List[TestCaseDTO]:
        """Фильтрация тест-кейсов по приоритету"""
        if not priority_filter:
            return testcases
        
        filtered = []
        for tc in testcases:
            if tc.priority in priority_filter:
                filtered.append(tc)
        
        self.logger.info(f"Отфильтровано {len(filtered)} из {len(testcases)} тест-кейсов")
        return filtered
    
    def _analyze_testcases(self, testcases: List[TestCaseDTO]) -> Dict[str, Any]:
        """Анализ тест-кейсов для планирования"""
        analysis = {
            "by_priority": {"CRITICAL": 0, "NORMAL": 0, "LOW": 0},
            "by_feature": {},
            "by_story": {},
            "estimated_duration": {"total_hours": 0, "by_priority": {}}
        }
        
        # Базовые оценки длительности по приоритету
        duration_estimates = {
            "CRITICAL": 0.25,  # 15 минут
            "NORMAL": 0.166,   # 10 минут
            "LOW": 0.083       # 5 минут
        }
        
        total_duration = 0
        
        for tc in testcases:
            # Подсчет по приоритету
            priority = tc.priority.value
            analysis["by_priority"][priority] += 1
            
            # Подсчет по фичам
            feature = tc.feature
            if feature not in analysis["by_feature"]:
                analysis["by_feature"][feature] = 0
            analysis["by_feature"][feature] += 1
            
            # Подсчет по историям
            story = tc.story
            if story not in analysis["by_story"]:
                analysis["by_story"][story] = 0
            analysis["by_story"][story] += 1
            
            # Оценка длительности
            tc_duration = duration_estimates.get(priority, 0.166)
            total_duration += tc_duration
            
            if priority not in analysis["estimated_duration"]["by_priority"]:
                analysis["estimated_duration"]["by_priority"][priority] = 0
            analysis["estimated_duration"]["by_priority"][priority] += tc_duration
        
        analysis["estimated_duration"]["total_hours"] = total_duration
        
        return analysis
    
    def _build_prompt(self, testcases: List[TestCaseDTO], 
                     analysis: Dict[str, Any], 
                     input_data: TestPlanInput) -> str:
        """Построение промпта для генерации тест-плана"""
        
        # Сводка по тест-кейсам
        testcases_summary = "\n".join([
            f"- {tc.title} [{tc.priority.value}] - {tc.feature}/{tc.story}"
            for tc in testcases[:20]  # Ограничиваем для промпта
        ])
        
        if len(testcases) > 20:
            testcases_summary += f"\n... и еще {len(testcases) - 20} тест-кейсов"
        
        prompt = f"""Ты - senior test lead, ответственный за планирование тестирования.

ТЕХНИЧЕСКОЕ ЗАДАНИЕ:
Создать профессиональный тест-план типа {input_data.plan_type.value.upper()}.

АНАЛИЗ ТЕСТ-КЕЙСОВ:
Всего тест-кейсов: {len(testcases)}
Распределение по приоритету: {json.dumps(analysis['by_priority'], ensure_ascii=False)}
Оценка длительности: {analysis['estimated_duration']['total_hours']:.2f} часов

ТЕСТ-КЕЙСЫ:
{testcases_summary}

{"ТРЕБОВАНИЯ ДЛЯ ТЕСТИРОВАНИЯ:" if input_data.requirements else ""}
{input_data.requirements if input_data.requirements else ""}

{"ЦЕЛЕВАЯ ДЛИТЕЛЬНОСТЬ: " + str(input_data.target_duration_hours) + " часов" if input_data.target_duration_hours else ""}

ИНСТРУКЦИИ ДЛЯ ТЕСТ-ПЛАНА:
1. Создать структурированный тест-план
2. Определить фазы тестирования
3. Распределить тест-кейсы по фазам
4. Оценить необходимые ресурсы
5. Создать график выполнения
6. Определить критерии входа/выхода
7. Провести оценку рисков
8. Определить метрики успеха

СТРУКТУРА ТЕСТ-ПЛАНА:
1. Обзор тест-плана (цель, объем, подход)
2. Фазы тестирования (название, описание, длительность, тест-кейсы)
3. Ресурсы (роли, количество, навыки)
4. График выполнения (даты, вехи)
5. Критерии входа/выхода для каждой фазы
6. Оценка рисков и митигации
7. Метрики и отчетность
8. Критерии завершения

ТИП ТЕСТ-ПЛАНА: {input_data.plan_type.value}
- regression: полное регрессионное тестирование
- smoke: быстрая проверка основной функциональности
- sanity: проверка критичных функций после изменений
- full: полное тестирование всех функций
- release: тестирование перед выпуском релиза

ФОРМАТ ОТВЕТА (JSON):
{{
    "test_plan": {{
        "title": "Название тест-плана",
        "type": "{input_data.plan_type.value}",
        "objective": "Цель тестирования",
        "scope": "Объем тестирования",
        "approach": "Подход к тестированию",
        "total_duration_hours": число,
        "success_criteria": ["критерий 1", "критерий 2"]
    }},
    "phases": [
        {{
            "name": "Название фазы",
            "description": "Описание фазы",
            "duration_hours": число,
            "objectives": ["цель 1", "цель 2"],
            "entry_criteria": ["критерий 1", "критерий 2"],
            "exit_criteria": ["критерий 1", "критерий 2"],
            "testcase_ids": ["список UUID тест-кейсов для фазы"]
        }}
    ],
    "resources": [
        {{
            "role": "роль (QA Engineer, Test Lead и т.д.)",
            "count": число,
            "skills": ["навык 1", "навык 2"],
            "responsibilities": ["ответственность 1", "ответственность 2"]
        }}
    ],
    "schedule": {{
        "start_date": "дата начала",
        "end_date": "дата завершения",
        "milestones": [
            {{
                "name": "название вехи",
                "date": "дата",
                "description": "описание"
            }}
        ]
    }},
    "risk_assessment": {{
        "risks": [
            {{
                "risk": "описание риска",
                "probability": "высокая/средняя/низкая",
                "impact": "высокое/среднее/низкое",
                "mitigation": "меры по снижению риска"
            }}
        ]
    }}
}}

ВАЖНО:
- План должен быть реалистичным и выполнимым
- Учитывать приоритеты тест-кейсов
- Распределить нагрузку равномерно
- Учесть время на setup/teardown
- Включить время на баг-фиксинг и ретест
- Определить четкие критерии успеха
"""
        return prompt
    
    def _parse_llm_response(self, llm_response: str) -> Dict[str, Any]:
        """Парсинг ответа LLM в структуру тест-плана"""
        try:
            import re
            
            # Извлечение JSON из ответа
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if not json_match:
                raise ValueError("Не удалось извлечь JSON из ответа LLM")
            
            data = json.loads(json_match.group())
            
            # Базовая валидация структуры
            required_sections = ["test_plan", "phases"]
            for section in required_sections:
                if section not in data:
                    raise ValueError(f"Отсутствует обязательный раздел: {section}")
            
            return data
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка парсинга JSON: {e}")
            raise ValueError(f"Некорректный JSON в ответе LLM: {str(e)}")
        except Exception as e:
            self.logger.error(f"Ошибка парсинга ответа LLM: {e}")
            raise
    
    def _enrich_plan_with_analysis(self, plan_data: Dict[str, Any], 
                                  analysis: Dict[str, Any],
                                  input_data: TestPlanInput) -> Dict[str, Any]:
        """Дополнение тест-плана данными из анализа"""
        enriched = plan_data.copy()
        
        # Добавление аналитики в тест-план
        if "test_plan" in enriched:
            enriched["test_plan"]["analysis_summary"] = {
                "total_testcases": len(input_data.testcases),
                "priority_distribution": analysis["by_priority"],
                "feature_coverage": len(analysis["by_feature"]),
                "estimated_duration_hours": analysis["estimated_duration"]["total_hours"]
            }
        
        # Корректировка длительности если указана целевая
        if input_data.target_duration_hours and "phases" in enriched:
            current_duration = sum(phase.get("duration_hours", 0) for phase in enriched["phases"])
            
            if current_duration > 0:
                ratio = input_data.target_duration_hours / current_duration
                
                # Масштабирование длительности фаз
                for phase in enriched["phases"]:
                    if "duration_hours" in phase:
                        phase["duration_hours"] = round(phase["duration_hours"] * ratio, 2)
                
                # Обновление общей длительности
                if "test_plan" in enriched and "total_duration_hours" in enriched["test_plan"]:
                    enriched["test_plan"]["total_duration_hours"] = round(
                        enriched["test_plan"]["total_duration_hours"] * ratio, 2
                    )
        
        return enriched
    
    def _create_phases(self, phases_data: List[Dict[str, Any]], 
                      testcases: List[TestCaseDTO]) -> List[TestPlanPhase]:
        """Создание объектов фаз тест-плана"""
        phases = []
        
        # Создаем маппинг тест-кейсов по ID для быстрого поиска
        testcases_by_id = {str(tc.id): tc for tc in testcases}
        
        for phase_data in phases_data:
            # Конвертация UUID строк в объекты UUID
            testcase_ids = []
            for tc_id_str in phase_data.get("testcase_ids", []):
                try:
                    tc_id = UUID(tc_id_str)
                    
                    # Проверка существования тест-кейса
                    if tc_id_str in testcases_by_id:
                        testcase_ids.append(tc_id)
                    else:
                        self.logger.warning(f"Тест-кейс {tc_id_str} не найден, исключен из фазы")
                except ValueError:
                    self.logger.warning(f"Некорректный UUID: {tc_id_str}")
            
            # Создание объекта фазы
            phase = TestPlanPhase(
                name=phase_data.get("name", "Unnamed Phase"),
                description=phase_data.get("description", ""),
                duration_hours=phase_data.get("duration_hours", 0),
                testcases=testcase_ids,
                objectives=phase_data.get("objectives", []),
                entry_criteria=phase_data.get("entry_criteria", []),
                exit_criteria=phase_data.get("exit_criteria", [])
            )
            phases.append(phase)
        
        return phases
    
    def _create_resources(self, resources_data: List[Dict[str, Any]]) -> List[TestPlanResource]:
        """Создание объектов ресурсов"""
        resources = []
        
        for resource_data in resources_data:
            resource = TestPlanResource(
                role=resource_data.get("role", "Unspecified"),
                count=resource_data.get("count", 1),
                skills=resource_data.get("skills", []),
                responsibilities=resource_data.get("responsibilities", [])
            )
            resources.append(resource)
        
        return resources
    
    def _load_plan_templates(self) -> Dict[str, Any]:
        """Загрузка шаблонов тест-планов"""
        return {
            "regression": {
                "phases": 3,
                "focus": "полное покрытие",
                "duration_ratio": 1.0
            },
            "smoke": {
                "phases": 1,
                "focus": "критичная функциональность",
                "duration_ratio": 0.2
            },
            "sanity": {
                "phases": 2,
                "focus": "основные функции после изменений",
                "duration_ratio": 0.4
            },
            "full": {
                "phases": 4,
                "focus": "все функции + дополнительные проверки",
                "duration_ratio": 1.5
            },
            "release": {
                "phases": 3,
                "focus": "стабильность и критические функции",
                "duration_ratio": 0.8
            }
        }