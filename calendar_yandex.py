"""Интеграция с Yandex Calendar API"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from config import Config

class YandexCalendar:
    """Класс для работы с Yandex Calendar"""
    
    AUTH_URL = "https://oauth.yandex.ru/authorize"
    TOKEN_URL = "https://oauth.yandex.ru/token"
    API_BASE_URL = "https://caldav.yandex.ru"
    
    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None):
        self.client_id = client_id or Config.get_yandex_client_id()
        self.client_secret = client_secret or Config.get_yandex_client_secret()
        self.redirect_uri = redirect_uri or Config.get_yandex_redirect_uri()
    
    def get_authorization_url(self, user_id: int = None) -> str:
        """Получение URL для авторизации
        
        Args:
            user_id: ID пользователя Telegram для связи через state параметр
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Логируем значения для отладки
        logger.info(f"Yandex OAuth: client_id={self.client_id[:10] + '...' if self.client_id and len(self.client_id) > 10 else self.client_id}, redirect_uri={self.redirect_uri}")
        
        if not self.client_id or self.client_id.strip() == '':
            logger.error("Yandex Client ID пустой или не установлен")
            raise ValueError("Yandex Client ID не установлен. Пожалуйста, настройте его в админ-панели: Настройки → Основные настройки")
        
        if not self.redirect_uri or self.redirect_uri.strip() == '':
            logger.error("Yandex Redirect URI пустой или не установлен")
            raise ValueError("Yandex Redirect URI не установлен. Пожалуйста, настройте его в админ-панели: Настройки → Основные настройки")
        
        import urllib.parse
        params = {
            'response_type': 'code',
            'client_id': self.client_id.strip(),  # Убираем пробелы
            'redirect_uri': self.redirect_uri.strip()  # Убираем пробелы
        }
        # Добавляем state с user_id, если передан
        if user_id:
            params['state'] = str(user_id)
        
        # Правильно кодируем параметры URL
        query_string = urllib.parse.urlencode(params)
        auth_url = f"{self.AUTH_URL}?{query_string}"
        
        logger.info(f"Yandex OAuth URL создан: {self.AUTH_URL}?client_id={params['client_id'][:10]}...&redirect_uri={params['redirect_uri'][:30]}...")
        
        return auth_url
    
    def get_token_from_code(self, code: str) -> Optional[Dict]:
        """Получение токена из кода авторизации"""
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'Bearer')
            }
        except Exception as e:
            print(f"Ошибка при получении токена: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict]:
        """Обновление access token"""
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()
            token_data = response.json()
            return {
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token', refresh_token),
                'expires_in': token_data.get('expires_in'),
                'token_type': token_data.get('token_type', 'Bearer')
            }
        except Exception as e:
            print(f"Ошибка при обновлении токена: {e}")
            return None
    
    def _make_request(self, access_token: str, method: str = 'GET', 
                     endpoint: str = '', data: dict = None) -> Optional[Dict]:
        """Выполнение запроса к API"""
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        url = f"{self.API_BASE_URL}/{endpoint}" if endpoint else self.API_BASE_URL
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                response = requests.request(method, url, headers=headers, json=data)
            
            response.raise_for_status()
            return response.json() if response.content else {}
        except Exception as e:
            print(f"Ошибка при запросе к API: {e}")
            return None
    
    def get_calendars(self, access_token: str) -> List[Dict]:
        """Получение списка календарей"""
        # Yandex Calendar использует CalDAV протокол
        # Для упрощения используем базовый API
        try:
            # Получаем информацию о пользователе
            user_info = self._make_request(access_token, 'GET', 'user')
            if user_info:
                return [{
                    'id': 'default',
                    'name': user_info.get('display_name', 'Yandex Calendar')
                }]
            return [{'id': 'default', 'name': 'Yandex Calendar'}]
        except Exception as e:
            print(f"Ошибка при получении календарей: {e}")
            return [{'id': 'default', 'name': 'Yandex Calendar'}]
    
    def get_upcoming_events(self, access_token: str,
                           time_min: datetime = None,
                           time_max: datetime = None,
                           max_results: int = 10) -> List[Dict]:
        """Получение предстоящих событий"""
        # Yandex Calendar использует CalDAV, что требует более сложной реализации
        # Для демонстрации используем упрощенный подход
        
        # В реальном проекте здесь должна быть реализация CalDAV запросов
        # или использование Yandex Calendar API, если он доступен
        
        try:
            # Пример запроса через CalDAV (упрощенная версия)
            # В реальности нужна полная реализация CalDAV клиента
            
            # Для демонстрации возвращаем пустой список
            # В продакшене здесь должна быть полная реализация CalDAV
            
            return []
            
        except Exception as e:
            print(f"Ошибка при получении событий: {e}")
            return []
    
    def get_calendar_info(self, access_token: str) -> Dict:
        """Получение информации о календаре"""
        try:
            user_info = self._make_request(access_token, 'GET', 'user')
            if user_info:
                return {
                    'id': 'default',
                    'name': user_info.get('display_name', 'Yandex Calendar')
                }
            return {'id': 'default', 'name': 'Yandex Calendar'}
        except Exception as e:
            print(f"Ошибка при получении информации: {e}")
            return {'id': 'default', 'name': 'Yandex Calendar'}

