"""Конфигурация приложения"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Класс конфигурации"""
    
    # Telegram - используем метод для получения токена из БД или .env
    @staticmethod
    def get_telegram_token():
        """Получение токена Telegram бота (из БД или .env)"""
        try:
            from database import Database
            db = Database()
            token = db.get_system_setting('telegram_bot_token')
            if token:
                return token
        except Exception:
            pass
        return os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Вспомогательный метод для получения настроек из БД или .env
    @staticmethod
    def _get_setting(key: str, default: str = ''):
        """Получение настройки из БД или .env"""
        try:
            from database import Database
            db = Database()
            value = db.get_system_setting(key)
            if value:
                return value
        except Exception:
            pass
        return os.getenv(key, default)
    
    # Google Calendar - используем методы для чтения из БД
    @staticmethod
    def get_google_client_id():
        return Config._get_setting('google_client_id', os.getenv('GOOGLE_CLIENT_ID', ''))
    
    @staticmethod
    def get_google_client_secret():
        return Config._get_setting('google_client_secret', os.getenv('GOOGLE_CLIENT_SECRET', ''))
    
    @staticmethod
    def get_google_redirect_uri():
        return Config._get_setting('google_redirect_uri', os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/callback/google'))
    
    GOOGLE_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
    
    # Yandex Calendar - используем методы для чтения из БД
    @staticmethod
    def get_yandex_client_id():
        return Config._get_setting('yandex_client_id', os.getenv('YANDEX_CLIENT_ID', ''))
    
    @staticmethod
    def get_yandex_client_secret():
        return Config._get_setting('yandex_client_secret', os.getenv('YANDEX_CLIENT_SECRET', ''))
    
    @staticmethod
    def get_yandex_redirect_uri():
        return Config._get_setting('yandex_redirect_uri', os.getenv('YANDEX_REDIRECT_URI', 'http://localhost:5000/callback/yandex'))
    
    YANDEX_SCOPES = ['caldav:read']
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///calendar_bot.db')
    
    # Flask
    FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', '5000'))
    
    # Notifications
    NOTIFICATION_TIME_MINUTES = int(os.getenv('NOTIFICATION_TIME_MINUTES', '15'))
    CHECK_INTERVAL_MINUTES = int(os.getenv('CHECK_INTERVAL_MINUTES', '5'))
    
    @staticmethod
    def validate():
        """Проверка обязательных параметров"""
        token = Config.get_telegram_token()
        if not token:
            raise ValueError("Отсутствует обязательный параметр: TELEGRAM_BOT_TOKEN")

