"""
Клиент для работы с GitLab API
"""
import os
from typing import Dict, List, Optional, Any
import base64
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.logger import get_logger
from src.utils.exceptions import GitLabException
from src.config import settings

logger = get_logger(__name__)


class GitLabClient:
    """
    Клиент для взаимодействия с GitLab API v4
    
    Документация: https://docs.gitlab.com/ee/api/
    Аутентификация: Private token или OAuth2
    """
    
    def __init__(
        self, 
        access_token: Optional[str] = None,
        project_id: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Инициализация клиента
        
        Args:
            access_token: GitLab Personal Access Token
            project_id: ID проекта GitLab
            base_url: URL GitLab (по умолчанию из настроек)
        """
        self.base_url = base_url or settings.GITLAB_URL
        self.access_token = access_token or settings.GITLAB_TOKEN
        self.project_id = project_id or settings.GITLAB_PROJECT_ID
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._get_headers(),
            timeout=30.0
        )
        
        logger.info(f"Initialized GitLab client for {self.base_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Получение заголовков для запросов"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"TestOps-Copilot/{settings.APP_VERSION}"
        }
        
        if self.access_token:
            headers["Private-Token"] = self.access_token
        
        return headers
    
    async def validate_connection(self) -> Dict[str, Any]:
        """
        Проверка соединения с GitLab
        
        Returns:
            Результат проверки соединения
        """
        try:
            # Пробуем получить информацию о пользователе
            response = await self.client.get("/api/v4/user")
            
            if response.status_code == 200:
                user_info = response.json()
                
                # Если указан project_id, проверяем доступ к проекту
                project_info = None
                if self.project_id:
                    try:
                        project_response = await self.client.get(f"/api/v4/projects/{self.project_id}")
                        if project_response.status_code == 200:
                            project_info = project_response.json()
                    except:
                        project_info = None
                
                return {
                    "available": True,
                    "authenticated": True,
                    "user": user_info.get("username"),
                    "project": project_info,
                    "base_url": self.base_url
                }
            elif response.status_code == 401:
                return {
                    "available": True,
                    "authenticated": False,
                    "error": "Invalid access token",
                    "base_url": self.base_url
                }
            else:
                return {
                    "available": False,
                    "authenticated": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "base_url": self.base_url
                }
                
        except httpx.ConnectError as e:
            logger.error(f"Connection error to GitLab: {e}")
            return {
                "available": False,
                "authenticated": False,
                "error": str(e),
                "base_url": self.base_url
            }
        except Exception as e:
            logger.error(f"Unexpected error validating GitLab connection: {e}")
            return {
                "available": False,
                "authenticated": False,
                "error": str(e),
                "base_url": self.base_url
            }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def upload_test_cases(
        self,
        test_cases: List[Dict[str, Any]],
        branch: str = "main",
        commit_message: str = "Add generated test cases",
        create_mr: bool = False,
        target_branch: Optional[str] = None,
        mr_title: Optional[str] = None,
        mr_description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Загрузка тест-кейсов в GitLab репозиторий
        
        Args:
            test_cases: Список тест-кейсов для загрузки
            branch: Ветка для коммита
            commit_message: Сообщение коммита
            create_mr: Создать merge request
            target_branch: Целевая ветка для MR
            mr_title: Заголовок MR
            mr_description: Описание MR
        
        Returns:
            Результат загрузки
        
        Raises:
            GitLabException: При ошибке API
        """
        if not self.project_id:
            raise GitLabException("Project ID не указан")
        
        try:
            # Создаем коммит с файлами
            actions = []
            
            for test_case in test_cases:
                filename = test_case.get("filename", f"test_{test_case.get('id', 'unknown')}.py")
                content = test_case.get("python_code", "")
                
                # Кодируем содержимое в base64
                content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                
                actions.append({
                    "action": "create",
                    "file_path": f"tests/{filename}",
                    "content": content_b64,
                    "encoding": "base64"
                })
            
            # Создаем коммит
            commit_data = {
                "branch": branch,
                "commit_message": commit_message,
                "actions": actions
            }
            
            logger.info(f"Creating commit with {len(actions)} files to branch {branch}")
            response = await self.client.post(
                f"/api/v4/projects/{self.project_id}/repository/commits",
                json=commit_data
            )
            
            if response.status_code != 201:
                raise GitLabException(f"Ошибка создания коммита: {response.text}")
            
            commit_result = response.json()
            
            # Создаем merge request если нужно
            mr_result = None
            if create_mr and target_branch and target_branch != branch:
                mr_data = {
                    "source_branch": branch,
                    "target_branch": target_branch,
                    "title": mr_title or f"Add test cases: {commit_message}",
                    "description": mr_description or f"Automatically generated test cases from TestOps Copilot\n\nFiles added:\n" + 
                                   "\n".join([f"- {a['file_path']}" for a in actions]),
                    "remove_source_branch": True
                }
                
                mr_response = await self.client.post(
                    f"/api/v4/projects/{self.project_id}/merge_requests",
                    json=mr_data
                )
                
                if mr_response.status_code == 201:
                    mr_result = mr_response.json()
                else:
                    logger.warning(f"Failed to create merge request: {mr_response.text}")
            
            return {
                "success": True,
                "commit": commit_result,
                "merge_request": mr_result,
                "files_uploaded": len(actions),
                "branch": branch
            }
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error uploading to GitLab: {e}")
            raise GitLabException(f"Ошибка загрузки в GitLab: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error uploading to GitLab: {e}")
            raise GitLabException(f"Неожиданная ошибка при загрузке в GitLab: {str(e)}")
    
    async def get_projects(self, search: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получение списка проектов
        
        Args:
            search: Поиск по названию
            limit: Максимальное количество
        
        Returns:
            Список проектов
        """
        try:
            params = {
                "membership": True,
                "per_page": limit
            }
            
            if search:
                params["search"] = search
            
            response = await self.client.get("/api/v4/projects", params=params)
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting GitLab projects: {e}")
            raise GitLabException(f"Ошибка получения списка проектов: {e.response.text}")
    
    async def get_branches(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Получение списка веток проекта
        
        Args:
            project_id: ID проекта (если не указан, используется инициализированный)
        
        Returns:
            Список веток
        """
        try:
            pid = project_id or self.project_id
            if not pid:
                raise GitLabException("Project ID не указан")
            
            response = await self.client.get(f"/api/v4/projects/{pid}/repository/branches")
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting GitLab branches: {e}")
            raise GitLabException(f"Ошибка получения списка веток: {e.response.text}")
    
    async def get_file_content(
        self, 
        file_path: str, 
        ref: str = "main",
        project_id: Optional[str] = None
    ) -> str:
        """
        Получение содержимого файла из репозитория
        
        Args:
            file_path: Путь к файлу
            ref: Ветка, тег или коммит
            project_id: ID проекта
        
        Returns:
            Содержимое файла
        """
        try:
            pid = project_id or self.project_id
            if not pid:
                raise GitLabException("Project ID не указан")
            
            response = await self.client.get(
                f"/api/v4/projects/{pid}/repository/files/{file_path}",
                params={"ref": ref}
            )
            response.raise_for_status()
            
            file_data = response.json()
            content_b64 = file_data.get("content", "")
            
            # Декодируем из base64
            return base64.b64decode(content_b64).decode("utf-8")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise GitLabException(f"Файл {file_path} не найден в ветке {ref}")
            else:
                raise GitLabException(f"Ошибка получения файла: {e.response.text}")
    
    async def create_issue(
        self,
        title: str,
        description: str,
        labels: Optional[List[str]] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создание issue в проекте
        
        Args:
            title: Заголовок issue
            description: Описание issue
            labels: Метки
            project_id: ID проекта
        
        Returns:
            Созданное issue
        """
        try:
            pid = project_id or self.project_id
            if not pid:
                raise GitLabException("Project ID не указан")
            
            issue_data = {
                "title": title,
                "description": description
            }
            
            if labels:
                issue_data["labels"] = ",".join(labels)
            
            response = await self.client.post(
                f"/api/v4/projects/{pid}/issues",
                json=issue_data
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating GitLab issue: {e}")
            raise GitLabException(f"Ошибка создания issue: {e.response.text}")
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Проверка здоровья GitLab соединения
        
        Returns:
            Статус здоровья
        """
        try:
            # Проверяем доступность API и аутентификацию
            response = await self.client.get("/api/v4/version", timeout=10.0)
            
            version_info = response.json() if response.status_code == 200 else None
            
            # Проверяем доступ к проекту если указан
            project_accessible = False
            project_info = None
            
            if self.project_id:
                try:
                    project_response = await self.client.get(
                        f"/api/v4/projects/{self.project_id}",
                        timeout=10.0
                    )
                    project_accessible = project_response.status_code == 200
                    if project_accessible:
                        project_info = project_response.json()
                except:
                    project_accessible = False
            
            return {
                "available": True,
                "version": version_info,
                "authenticated": self.access_token is not None,
                "project_accessible": project_accessible,
                "project": project_info,
                "base_url": self.base_url,
                "timestamp": self._get_timestamp()
            }
            
        except Exception as e:
            logger.error(f"GitLab health check failed: {e}")
            return {
                "available": False,
                "error": str(e),
                "base_url": self.base_url
            }
    
    def _get_timestamp(self) -> str:
        """Получение текущей метки времени"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def close(self):
        """Закрытие клиента"""
        await self.client.aclose()
        logger.info("GitLab client closed")


# Фабрика для dependency injection
def get_gitlab_client():
    """Получение клиента GitLab"""
    return GitLabClient()