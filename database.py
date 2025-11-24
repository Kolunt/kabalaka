"""Работа с базой данных"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
from contextlib import contextmanager

class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = 'calendar_bot.db'):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для подключения к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_db(self):
        """Инициализация базы данных"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    language TEXT DEFAULT 'en',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Добавляем колонку language, если её нет (для существующих БД)
            try:
                cursor.execute('ALTER TABLE users ADD COLUMN language TEXT DEFAULT \'en\'')
            except sqlite3.OperationalError:
                pass  # Колонка уже существует
            
            # Таблица подключений к календарям
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS calendar_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    calendar_type TEXT NOT NULL,
                    access_token TEXT,
                    refresh_token TEXT,
                    token_expires_at TIMESTAMP,
                    calendar_id TEXT,
                    calendar_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, calendar_type)
                )
            ''')
            
            # Таблица настроек уведомлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification_settings (
                    user_id INTEGER PRIMARY KEY,
                    notification_minutes INTEGER DEFAULT 15,
                    enabled BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Таблица отправленных уведомлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sent_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    calendar_type TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    event_start_time TIMESTAMP NOT NULL,
                    notified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, calendar_type, event_id, event_start_time)
                )
            ''')
            
            # Таблица администраторов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица настроек системы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
    
    def add_user(self, user_id: int, username: Optional[str] = None, first_name: Optional[str] = None):
        """Добавление пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name)
                VALUES (?, ?, ?)
            ''', (user_id, username, first_name))
    
    def save_calendar_connection(self, user_id: int, calendar_type: str, 
                                 access_token: str, refresh_token: Optional[str] = None,
                                 token_expires_at: Optional[datetime] = None,
                                 calendar_id: Optional[str] = None,
                                 calendar_name: Optional[str] = None):
        """Сохранение подключения к календарю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO calendar_connections 
                (user_id, calendar_type, access_token, refresh_token, 
                 token_expires_at, calendar_id, calendar_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, calendar_type, access_token, refresh_token,
                  token_expires_at, calendar_id, calendar_name))
    
    def get_calendar_connection(self, user_id: int, calendar_type: str) -> Optional[Dict]:
        """Получение подключения к календарю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM calendar_connections
                WHERE user_id = ? AND calendar_type = ?
            ''', (user_id, calendar_type))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_user_calendars(self, user_id: int) -> List[Dict]:
        """Получение всех календарей пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT calendar_type, calendar_name, calendar_id
                FROM calendar_connections
                WHERE user_id = ?
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_calendar_connection(self, user_id: int, calendar_type: str):
        """Удаление подключения к календарю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM calendar_connections
                WHERE user_id = ? AND calendar_type = ?
            ''', (user_id, calendar_type))
    
    def update_notification_settings(self, user_id: int, notification_minutes: int, enabled: bool = True):
        """Обновление настроек уведомлений"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO notification_settings 
                (user_id, notification_minutes, enabled)
                VALUES (?, ?, ?)
            ''', (user_id, notification_minutes, enabled))
    
    def get_notification_settings(self, user_id: int) -> Dict:
        """Получение настроек уведомлений"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT notification_minutes, enabled
                FROM notification_settings
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {'notification_minutes': 15, 'enabled': True}
    
    def mark_notification_sent(self, user_id: int, calendar_type: str, 
                               event_id: str, event_start_time: datetime):
        """Отметка об отправленном уведомлении"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO sent_notifications 
                (user_id, calendar_type, event_id, event_start_time)
                VALUES (?, ?, ?, ?)
            ''', (user_id, calendar_type, event_id, event_start_time))
    
    def is_notification_sent(self, user_id: int, calendar_type: str, 
                             event_id: str, event_start_time: datetime) -> bool:
        """Проверка, было ли отправлено уведомление"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) as count FROM sent_notifications
                WHERE user_id = ? AND calendar_type = ? 
                AND event_id = ? AND event_start_time = ?
            ''', (user_id, calendar_type, event_id, event_start_time))
            row = cursor.fetchone()
            return row['count'] > 0
    
    def get_all_active_users(self) -> List[int]:
        """Получение всех пользователей с подключенными календарями"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT user_id FROM calendar_connections
            ''')
            return [row['user_id'] for row in cursor.fetchall()]
    
    def get_all_users(self) -> List[Dict]:
        """Получение всех пользователей с информацией"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.*, 
                       COUNT(DISTINCT cc.id) as calendar_count,
                       COUNT(DISTINCT sn.id) as notification_count
                FROM users u
                LEFT JOIN calendar_connections cc ON u.user_id = cc.user_id
                LEFT JOIN sent_notifications sn ON u.user_id = sn.user_id
                GROUP BY u.user_id
                ORDER BY u.created_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_user_details(self, user_id: int) -> Optional[Dict]:
        """Получение детальной информации о пользователе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.*, 
                       COUNT(DISTINCT cc.id) as calendar_count,
                       COUNT(DISTINCT sn.id) as notification_count
                FROM users u
                LEFT JOIN calendar_connections cc ON u.user_id = cc.user_id
                LEFT JOIN sent_notifications sn ON u.user_id = sn.user_id
                WHERE u.user_id = ?
                GROUP BY u.user_id
            ''', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_statistics(self) -> Dict:
        """Получение статистики системы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Общее количество пользователей
            cursor.execute('SELECT COUNT(*) as count FROM users')
            stats['total_users'] = cursor.fetchone()['count']
            
            # Активные пользователи (с календарями)
            cursor.execute('SELECT COUNT(DISTINCT user_id) as count FROM calendar_connections')
            stats['active_users'] = cursor.fetchone()['count']
            
            # Количество подключенных календарей
            cursor.execute('SELECT COUNT(*) as count FROM calendar_connections')
            stats['total_calendars'] = cursor.fetchone()['count']
            
            # Google календари
            cursor.execute('SELECT COUNT(*) as count FROM calendar_connections WHERE calendar_type = "google"')
            stats['google_calendars'] = cursor.fetchone()['count']
            
            # Yandex календари
            cursor.execute('SELECT COUNT(*) as count FROM calendar_connections WHERE calendar_type = "yandex"')
            stats['yandex_calendars'] = cursor.fetchone()['count']
            
            # Отправленных уведомлений
            cursor.execute('SELECT COUNT(*) as count FROM sent_notifications')
            stats['total_notifications'] = cursor.fetchone()['count']
            
            # Уведомлений за последние 24 часа
            cursor.execute('''
                SELECT COUNT(*) as count FROM sent_notifications 
                WHERE notified_at >= datetime('now', '-1 day')
            ''')
            stats['notifications_24h'] = cursor.fetchone()['count']
            
            return stats
    
    def create_admin(self, username: str, password_hash: str):
        """Создание администратора"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO admins (username, password_hash)
                VALUES (?, ?)
            ''', (username, password_hash))
    
    def get_admin(self, username: str) -> Optional[Dict]:
        """Получение администратора по username"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM admins WHERE username = ?', (username,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_system_setting(self, key: str) -> Optional[str]:
        """Получение настройки системы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM system_settings WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                return row['value']
            return None
    
    def set_system_setting(self, key: str, value: str):
        """Установка настройки системы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO system_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (key, value))
    
    def get_all_system_settings(self) -> Dict[str, str]:
        """Получение всех настроек системы"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT key, value FROM system_settings')
            return {row['key']: row['value'] for row in cursor.fetchall()}
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def update_user_language(self, user_id: int, language: str):
        """Обновление языка пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users SET language = ? WHERE user_id = ?
            ''', (language, user_id))

