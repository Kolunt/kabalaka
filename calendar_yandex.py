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
        """Получение предстоящих событий через CalDAV"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Yandex Calendar использует CalDAV протокол
            # Для работы с OAuth токеном используем ручную реализацию через requests
            
            if time_min is None:
                time_min = datetime.utcnow()
            if time_max is None:
                time_max = time_min + timedelta(days=1)
            
            # Форматируем даты для CalDAV запроса (RFC 3339)
            time_min_str = time_min.strftime('%Y%m%dT%H%M%SZ')
            time_max_str = time_max.strftime('%Y%m%dT%H%M%SZ')
            
            # URL для CalDAV запроса событий
            # Yandex использует стандартный CalDAV endpoint
            # Пробуем несколько вариантов endpoints
            caldav_urls = [
                f"{self.API_BASE_URL}/events/",
                f"{self.API_BASE_URL}/calendars/",
                f"{self.API_BASE_URL}/",
            ]
            
            # CalDAV REPORT запрос для получения событий в диапазоне дат
            # Используем calendar-query для фильтрации по времени
            caldav_query = f"""<?xml version="1.0" encoding="utf-8" ?>
<C:calendar-query xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
    <D:prop>
        <D:getetag/>
        <C:calendar-data/>
    </D:prop>
    <C:filter>
        <C:comp-filter name="VCALENDAR">
            <C:comp-filter name="VEVENT">
                <C:time-range start="{time_min_str}" end="{time_max_str}"/>
            </C:comp-filter>
        </C:comp-filter>
    </C:filter>
</C:calendar-query>"""
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/xml; charset=utf-8',
                'Depth': '1'
            }
            
            logger.info(f"Yandex CalDAV: запрос событий с {time_min_str} по {time_max_str}")
            
            # Пробуем разные endpoints
            events = []
            for caldav_url in caldav_urls:
                try:
                    logger.debug(f"Пробуем endpoint: {caldav_url}")
                    # Выполняем REPORT запрос
                    response = requests.request('REPORT', caldav_url, headers=headers, data=caldav_query, timeout=10)
                    
                    if response.status_code == 401:
                        logger.warning(f"Yandex CalDAV: ошибка авторизации (401) для {caldav_url}")
                        continue
                    
                    if response.status_code == 404:
                        logger.debug(f"Yandex CalDAV: календарь не найден (404) для {caldav_url}")
                        continue
                    
                    if response.status_code == 207:  # 207 Multi-Status - стандартный ответ CalDAV
                        # Парсим ответ CalDAV (iCalendar формат)
                        events = self._parse_caldav_response(response.text, time_min, time_max)
                        if events:
                            logger.info(f"Yandex CalDAV: успешно получены события через {caldav_url}")
                            break
                    
                    if response.status_code not in [207, 401, 404]:
                        logger.debug(f"Yandex CalDAV: статус {response.status_code} для {caldav_url}: {response.text[:200]}")
                        
                except Exception as e:
                    logger.debug(f"Ошибка при запросе к {caldav_url}: {e}")
                    continue
            
            # Если не получили события через CalDAV, пробуем альтернативный метод
            if not events:
                logger.warning("Yandex CalDAV: не удалось получить события через стандартный CalDAV. Пробуем альтернативный метод.")
                events = self._get_events_alternative(access_token, time_min, time_max, max_results)
            
            logger.info(f"Yandex CalDAV: получено {len(events)} событий")
            return events[:max_results]
            
        except Exception as e:
            logger.error(f"Ошибка при получении событий Yandex Calendar: {e}", exc_info=True)
            # Пробуем альтернативный подход при ошибке
            try:
                return self._get_events_alternative(access_token, time_min, time_max, max_results)
            except Exception as e2:
                logger.error(f"Альтернативный метод также не сработал: {e2}")
                return []
    
    def _get_events_alternative(self, access_token: str, time_min: datetime, time_max: datetime, max_results: int) -> List[Dict]:
        """Альтернативный метод получения событий через библиотеку caldav"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Пробуем использовать библиотеку caldav
            import caldav
            
            # Для Yandex с OAuth нужно использовать специальный подход
            # Yandex CalDAV может требовать логин пользователя вместо токена
            # Пока возвращаем пустой список, так как нужна информация о пользователе
            
            logger.warning("Yandex CalDAV: альтернативный метод не реализован. Требуется информация о пользователе.")
            return []
            
        except ImportError:
            logger.warning("Библиотека caldav не установлена. Установите: pip install caldav")
            return []
        except Exception as e:
            logger.error(f"Ошибка в альтернативном методе: {e}")
            return []
    
    def _parse_caldav_response(self, ical_data: str, time_min: datetime, time_max: datetime) -> List[Dict]:
        """Парсинг iCalendar данных из CalDAV ответа"""
        import logging
        import re
        from dateutil import parser as date_parser
        
        logger = logging.getLogger(__name__)
        events = []
        
        try:
            # Разделяем ответ на отдельные события (каждое событие в своем блоке)
            # CalDAV возвращает несколько VCALENDAR блоков, каждый содержит VEVENT
            
            # Ищем все блоки VEVENT
            vevent_pattern = r'BEGIN:VEVENT(.*?)END:VEVENT'
            vevents = re.findall(vevent_pattern, ical_data, re.DOTALL)
            
            logger.debug(f"Найдено VEVENT блоков: {len(vevents)}")
            
            for vevent_text in vevents:
                try:
                    event_data = {}
                    
                    # Извлекаем основные поля
                    # UID
                    uid_match = re.search(r'UID:(.*?)(?:\r\n|\n)', vevent_text)
                    if uid_match:
                        event_data['id'] = uid_match.group(1).strip()
                    else:
                        continue  # Пропускаем события без UID
                    
                    # SUMMARY (название)
                    summary_match = re.search(r'SUMMARY(?:;.*?)?:(.*?)(?:\r\n|\n)', vevent_text)
                    if summary_match:
                        event_data['summary'] = summary_match.group(1).strip()
                    else:
                        event_data['summary'] = 'Без названия'
                    
                    # DESCRIPTION
                    desc_match = re.search(r'DESCRIPTION(?:;.*?)?:(.*?)(?:\r\n|\n)', vevent_text, re.DOTALL)
                    if desc_match:
                        # Убираем переносы строк и экранирование
                        description = desc_match.group(1).strip()
                        description = description.replace('\\n', '\n').replace('\\,', ',')
                        event_data['description'] = description
                    else:
                        event_data['description'] = ''
                    
                    # LOCATION
                    location_match = re.search(r'LOCATION(?:;.*?)?:(.*?)(?:\r\n|\n)', vevent_text)
                    if location_match:
                        location = location_match.group(1).strip()
                        location = location.replace('\\,', ',')
                        event_data['location'] = location
                    else:
                        event_data['location'] = ''
                    
                    # DTSTART (время начала)
                    dtstart_match = re.search(r'DTSTART(?:;.*?)?:(.*?)(?:\r\n|\n)', vevent_text)
                    if dtstart_match:
                        dtstart_str = dtstart_match.group(1).strip()
                        try:
                            # Парсим формат iCalendar (YYYYMMDDTHHMMSS или YYYYMMDD)
                            if 'T' in dtstart_str:
                                if len(dtstart_str) == 15:  # YYYYMMDDTHHMMSS
                                    start_dt = datetime.strptime(dtstart_str, '%Y%m%dT%H%M%S')
                                elif len(dtstart_str) == 16 and dtstart_str.endswith('Z'):  # YYYYMMDDTHHMMSSZ
                                    start_dt = datetime.strptime(dtstart_str, '%Y%m%dT%H%M%SZ')
                                else:
                                    start_dt = date_parser.parse(dtstart_str)
                            else:
                                # Только дата
                                start_dt = datetime.strptime(dtstart_str, '%Y%m%d')
                            event_data['start'] = start_dt
                        except Exception as e:
                            logger.warning(f"Ошибка парсинга DTSTART '{dtstart_str}': {e}")
                            continue
                    else:
                        continue  # Пропускаем события без времени начала
                    
                    # DTEND (время окончания)
                    dtend_match = re.search(r'DTEND(?:;.*?)?:(.*?)(?:\r\n|\n)', vevent_text)
                    if dtend_match:
                        dtend_str = dtend_match.group(1).strip()
                        try:
                            if 'T' in dtend_str:
                                if len(dtend_str) == 15:
                                    end_dt = datetime.strptime(dtend_str, '%Y%m%dT%H%M%S')
                                elif len(dtend_str) == 16 and dtend_str.endswith('Z'):
                                    end_dt = datetime.strptime(dtend_str, '%Y%m%dT%H%M%SZ')
                                else:
                                    end_dt = date_parser.parse(dtend_str)
                            else:
                                end_dt = datetime.strptime(dtend_str, '%Y%m%d')
                            event_data['end'] = end_dt
                        except Exception as e:
                            logger.warning(f"Ошибка парсинга DTEND '{dtend_str}': {e}")
                            # Если не удалось распарсить, используем start + 1 час
                            event_data['end'] = event_data['start'] + timedelta(hours=1)
                    else:
                        # Если нет DTEND, используем start + 1 час
                        event_data['end'] = event_data['start'] + timedelta(hours=1)
                    
                    # Фильтруем события по времени (на всякий случай, хотя фильтр уже в запросе)
                    if time_min <= event_data['start'] <= time_max:
                        events.append(event_data)
                    
                except Exception as e:
                    logger.warning(f"Ошибка при парсинге события: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге CalDAV ответа: {e}", exc_info=True)
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

