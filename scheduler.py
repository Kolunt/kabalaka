"""Планировщик проверки событий"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from database import Database
from calendar_google import GoogleCalendar
from calendar_yandex import YandexCalendar
from telegram import Bot
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()
google_cal = GoogleCalendar()
yandex_cal = YandexCalendar()

async def check_and_notify_events():
    """Проверка событий и отправка уведомлений"""
    try:
        token = Config.get_telegram_token()
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN не установлен. Пропуск проверки событий.")
            return
        bot = Bot(token=token)
        active_users = db.get_all_active_users()
        
        for user_id in active_users:
            try:
                settings = db.get_notification_settings(user_id)
                if not settings.get('enabled', True):
                    continue
                
                notification_minutes = settings.get('notification_minutes', 15)
                
                # Получаем все календари пользователя
                calendars = db.get_user_calendars(user_id)
                
                for cal_info in calendars:
                    calendar_type = cal_info['calendar_type']
                    connection = db.get_calendar_connection(user_id, calendar_type)
                    
                    if not connection:
                        continue
                    
                    # Получаем события
                    connection['user_id'] = user_id  # Добавляем user_id для использования в функции
                    events = await get_events_for_calendar(connection, calendar_type)
                    
                    # Фильтруем события, которые нужно уведомить
                    now = datetime.utcnow()
                    target_time = now + timedelta(minutes=notification_minutes)
                    
                    for event in events:
                        event_start = event['start']
                        
                        # Проверяем, нужно ли отправить уведомление
                        if now <= event_start <= target_time:
                            # Проверяем, не отправляли ли уже уведомление
                            if not db.is_notification_sent(user_id, calendar_type, 
                                                          event['id'], event_start):
                                await send_notification(bot, user_id, event, calendar_type)
                                db.mark_notification_sent(user_id, calendar_type, 
                                                         event['id'], event_start)
            
            except Exception as e:
                logger.error(f"Ошибка при обработке пользователя {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Ошибка при проверке событий: {e}")

async def get_events_for_calendar(connection: Dict, calendar_type: str) -> List[Dict]:
    """Получение событий для календаря"""
    try:
        if calendar_type == 'google':
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            
            # Восстанавливаем credentials
            token_data = {
                'token': connection['access_token'],
                'refresh_token': connection.get('refresh_token'),
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': Config.GOOGLE_CLIENT_ID,
                'client_secret': Config.GOOGLE_CLIENT_SECRET,
                'scopes': Config.GOOGLE_SCOPES
            }
            
            creds = Credentials.from_authorized_user_info(token_data)
            
            # Обновляем токен, если истек
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # Сохраняем обновленный токен
                db.save_calendar_connection(
                    user_id=connection['user_id'],
                    calendar_type='google',
                    access_token=creds.token,
                    refresh_token=creds.refresh_token,
                    token_expires_at=creds.expiry,
                    calendar_id=connection.get('calendar_id'),
                    calendar_name=connection.get('calendar_name')
                )
            
            time_min = datetime.utcnow()
            time_max = time_min + timedelta(days=1)
            
            return google_cal.get_upcoming_events(creds, time_min, time_max, max_results=50)
        
        elif calendar_type == 'yandex':
            access_token = connection['access_token']
            
            # Проверяем, не истек ли токен
            if connection.get('token_expires_at'):
                try:
                    expires_at_str = connection['token_expires_at']
                    if isinstance(expires_at_str, str):
                        # Обработка разных форматов даты
                        expires_at_str = expires_at_str.replace('Z', '+00:00')
                        if '+' not in expires_at_str and expires_at_str.count(':') == 1:
                            expires_at_str += '+00:00'
                        expires_at = datetime.fromisoformat(expires_at_str)
                    else:
                        expires_at = expires_at_str
                    if expires_at <= datetime.utcnow() and connection.get('refresh_token'):
                        # Обновляем токен
                        new_token_data = yandex_cal.refresh_access_token(connection['refresh_token'])
                        if new_token_data:
                            expires_at = datetime.utcnow() + timedelta(seconds=new_token_data.get('expires_in', 3600))
                            db.save_calendar_connection(
                                user_id=connection['user_id'],
                                calendar_type='yandex',
                                access_token=new_token_data['access_token'],
                                refresh_token=new_token_data.get('refresh_token'),
                                token_expires_at=expires_at,
                                calendar_id=connection.get('calendar_id'),
                                calendar_name=connection.get('calendar_name')
                            )
                            access_token = new_token_data['access_token']
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Ошибка при обработке даты истечения токена: {e}")
            
            time_min = datetime.utcnow()
            time_max = time_min + timedelta(days=1)
            
            return yandex_cal.get_upcoming_events(access_token, time_min, time_max, max_results=50)
        
        return []
    
    except Exception as e:
        logger.error(f"Ошибка при получении событий для {calendar_type}: {e}")
        return []

async def send_notification(bot: Bot, user_id: int, event: Dict, calendar_type: str):
    """Отправка уведомления о событии"""
    try:
        event_start = event['start']
        time_until = event_start - datetime.utcnow()
        minutes_until = int(time_until.total_seconds() / 60)
        
        calendar_name = "Google Calendar" if calendar_type == 'google' else "Yandex Calendar"
        
        message = (
            f"🔔 Напоминание о событии\n\n"
            f"📅 {event['summary']}\n"
            f"⏰ Начало через {minutes_until} минут\n"
            f"🕐 {event_start.strftime('%d.%m.%Y %H:%M')}\n"
        )
        
        if event.get('location'):
            message += f"📍 {event['location']}\n"
        
        if event.get('description'):
            desc = event['description'][:200]
            if len(event['description']) > 200:
                desc += "..."
            message += f"\n📝 {desc}\n"
        
        message += f"\n📱 Календарь: {calendar_name}"
        
        if event.get('htmlLink'):
            message += f"\n🔗 {event['htmlLink']}"
        
        await bot.send_message(chat_id=user_id, text=message)
        logger.info(f"Уведомление отправлено пользователю {user_id} о событии {event['id']}")
    
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления: {e}")

