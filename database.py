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
            
            # Таблица рассылок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT NOT NULL,
                    languages TEXT,  -- JSON массив языков, например ["en", "ru", "es"] или null для всех
                    scheduled_at TIMESTAMP,  -- null для немедленной отправки
                    status TEXT DEFAULT 'pending',  -- pending, sending, completed, failed
                    created_by TEXT,  -- username администратора
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    total_users INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0
                )
            ''')
            
            # Таблица истории отправок рассылок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcast_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    broadcast_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    language TEXT,
                    status TEXT NOT NULL,  -- sent, failed, skipped
                    error_message TEXT,
                    sent_at TIMESTAMP,
                    FOREIGN KEY (broadcast_id) REFERENCES broadcasts(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(broadcast_id, user_id)
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
    
    def get_user_language(self, user_id: int) -> Optional[str]:
        """Получение языка пользователя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT language FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return row['language'] or 'en'
            return 'en'
    
    # Методы для работы с рассылками
    def create_broadcast(self, message_text: str, languages: Optional[List[str]] = None, 
                        scheduled_at: Optional[datetime] = None, created_by: str = 'admin') -> int:
        """Создание новой рассылки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            languages_json = json.dumps(languages) if languages else None
            cursor.execute('''
                INSERT INTO broadcasts (message_text, languages, scheduled_at, created_by, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (message_text, languages_json, scheduled_at, created_by))
            return cursor.lastrowid
    
    def get_broadcast(self, broadcast_id: int) -> Optional[Dict]:
        """Получение информации о рассылке"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM broadcasts WHERE id = ?', (broadcast_id,))
            row = cursor.fetchone()
            if row:
                result = dict(row)
                if result.get('languages'):
                    result['languages'] = json.loads(result['languages'])
                return result
            return None
    
    def get_all_broadcasts(self, limit: int = 50) -> List[Dict]:
        """Получение всех рассылок"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM broadcasts 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result.get('languages'):
                    result['languages'] = json.loads(result['languages'])
                results.append(result)
            return results
    
    def update_broadcast_status(self, broadcast_id: int, status: str, 
                               sent_count: int = 0, failed_count: int = 0):
        """Обновление статуса рассылки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status == 'sending' and sent_count == 0 and failed_count == 0:
                cursor.execute('''
                    UPDATE broadcasts 
                    SET status = ?, started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (status, broadcast_id))
            elif status in ('completed', 'failed'):
                cursor.execute('''
                    UPDATE broadcasts 
                    SET status = ?, completed_at = CURRENT_TIMESTAMP,
                        sent_count = ?, failed_count = ?
                    WHERE id = ?
                ''', (status, sent_count, failed_count, broadcast_id))
            else:
                cursor.execute('''
                    UPDATE broadcasts 
                    SET status = ?, sent_count = ?, failed_count = ?
                    WHERE id = ?
                ''', (status, sent_count, failed_count, broadcast_id))
    
    def set_broadcast_total_users(self, broadcast_id: int, total_users: int):
        """Установка общего количества пользователей для рассылки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE broadcasts SET total_users = ? WHERE id = ?
            ''', (total_users, broadcast_id))
    
    def add_broadcast_history(self, broadcast_id: int, user_id: int, 
                             language: Optional[str], status: str, 
                             error_message: Optional[str] = None):
        """Добавление записи в историю рассылки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            sent_at = datetime.utcnow() if status == 'sent' else None
            cursor.execute('''
                INSERT OR REPLACE INTO broadcast_history 
                (broadcast_id, user_id, language, status, error_message, sent_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (broadcast_id, user_id, language, status, error_message, sent_at))
    
    def get_broadcast_history(self, broadcast_id: int) -> List[Dict]:
        """Получение истории рассылки"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT bh.*, u.username, u.first_name
                FROM broadcast_history bh
                LEFT JOIN users u ON bh.user_id = u.user_id
                WHERE bh.broadcast_id = ?
                ORDER BY bh.sent_at DESC, bh.id DESC
            ''', (broadcast_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_users_by_languages(self, languages: Optional[List[str]] = None) -> List[Dict]:
        """Получение пользователей по языкам"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if languages:
                placeholders = ','.join(['?'] * len(languages))
                cursor.execute(f'''
                    SELECT user_id, language, username, first_name
                    FROM users
                    WHERE language IN ({placeholders}) OR language IS NULL
                ''', languages)
            else:
                cursor.execute('''
                    SELECT user_id, language, username, first_name
                    FROM users
                ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_pending_broadcasts(self) -> List[Dict]:
        """Получение рассылок, готовых к отправке"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM broadcasts 
                WHERE status = 'pending' 
                AND (scheduled_at IS NULL OR scheduled_at <= CURRENT_TIMESTAMP)
                ORDER BY created_at ASC
            ''')
            results = []
            for row in cursor.fetchall():
                result = dict(row)
                if result.get('languages'):
                    result['languages'] = json.loads(result['languages'])
                results.append(result)
            return results

