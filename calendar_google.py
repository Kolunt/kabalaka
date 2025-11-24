"""Интеграция с Google Calendar API"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
from config import Config

class GoogleCalendar:
    """Класс для работы с Google Calendar"""
    
    SCOPES = Config.GOOGLE_SCOPES
    
    def __init__(self, client_id: str = None, client_secret: str = None, redirect_uri: str = None):
        self.client_id = client_id or Config.GOOGLE_CLIENT_ID
        self.client_secret = client_secret or Config.GOOGLE_CLIENT_SECRET
        self.redirect_uri = redirect_uri or Config.GOOGLE_REDIRECT_URI
    
    def get_authorization_url(self) -> str:
        """Получение URL для авторизации"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return authorization_url
    
    def get_credentials_from_code(self, code: str) -> Credentials:
        """Получение credentials из кода авторизации"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        flow.fetch_token(code=code)
        return flow.credentials
    
    def get_credentials_from_token(self, token_data: dict) -> Optional[Credentials]:
        """Создание credentials из сохраненного токена"""
        try:
            creds = Credentials.from_authorized_user_info(token_data)
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
        except Exception as e:
            print(f"Ошибка при создании credentials: {e}")
            return None
    
    def get_upcoming_events(self, credentials: Credentials, 
                           time_min: datetime = None, 
                           time_max: datetime = None,
                           max_results: int = 10) -> List[Dict]:
        """Получение предстоящих событий"""
        try:
            service = build('calendar', 'v3', credentials=credentials)
            
            if time_min is None:
                time_min = datetime.utcnow()
            if time_max is None:
                time_max = time_min + timedelta(days=7)
            
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min.isoformat() + 'Z',
                timeMax=time_max.isoformat() + 'Z',
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            result = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Парсинг времени
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start)
                
                if 'T' in end:
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                else:
                    end_dt = datetime.fromisoformat(end)
                
                result.append({
                    'id': event.get('id'),
                    'summary': event.get('summary', 'Без названия'),
                    'description': event.get('description', ''),
                    'start': start_dt,
                    'end': end_dt,
                    'location': event.get('location', ''),
                    'htmlLink': event.get('htmlLink', ''),
                    'calendar_type': 'google'
                })
            
            return result
            
        except HttpError as error:
            print(f'Ошибка при получении событий: {error}')
            return []
        except Exception as e:
            print(f'Неожиданная ошибка: {e}')
            return []
    
    def get_calendar_info(self, credentials: Credentials) -> Dict:
        """Получение информации о календаре"""
        try:
            service = build('calendar', 'v3', credentials=credentials)
            calendar = service.calendars().get(calendarId='primary').execute()
            return {
                'id': calendar.get('id'),
                'name': calendar.get('summary', 'Primary Calendar')
            }
        except Exception as e:
            print(f'Ошибка при получении информации о календаре: {e}')
            return {'id': 'primary', 'name': 'Google Calendar'}

