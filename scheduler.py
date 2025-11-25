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
        logger.info("=== Начало проверки событий ===")
        token = Config.get_telegram_token()
        if not token:
            logger.warning("TELEGRAM_BOT_TOKEN не установлен. Пропуск проверки событий.")
            return
        bot = Bot(token=token)
        active_users = db.get_all_active_users()
        logger.info(f"Найдено активных пользователей: {len(active_users)}")
        
        if not active_users:
            logger.info("Нет активных пользователей с подключенными календарями")
            return
        
        for user_id in active_users:
            try:
                logger.info(f"Обработка пользователя {user_id}")
                settings = db.get_notification_settings(user_id)
                if not settings.get('enabled', True):
                    logger.info(f"Уведомления отключены для пользователя {user_id}")
                    continue
                
                notification_minutes = settings.get('notification_minutes', 15)
                logger.info(f"Интервал уведомлений для пользователя {user_id}: {notification_minutes} минут")
                
                # Получаем все календари пользователя
                calendars = db.get_user_calendars(user_id)
                logger.info(f"Найдено календарей для пользователя {user_id}: {len(calendars)}")
                
                for cal_info in calendars:
                    calendar_type = cal_info['calendar_type']
                    logger.info(f"Обработка календаря {calendar_type} для пользователя {user_id}")
                    connection = db.get_calendar_connection(user_id, calendar_type)
                    
                    if not connection:
                        logger.warning(f"Подключение {calendar_type} не найдено для пользователя {user_id}")
                        continue
                    
                    # Получаем события
                    connection['user_id'] = user_id  # Добавляем user_id для использования в функции
                    events = await get_events_for_calendar(connection, calendar_type)
                    logger.info(f"Получено событий из {calendar_type} для пользователя {user_id}: {len(events)}")
                    
                    # Фильтруем события, которые нужно уведомить
                    now = datetime.utcnow()
                    target_time = now + timedelta(minutes=notification_minutes)
                    logger.info(f"Проверка событий между {now} и {target_time}")
                    
                    events_to_notify = 0
                    for event in events:
                        event_start = event['start']
                        logger.debug(f"Событие: {event.get('summary', 'N/A')} в {event_start}")
                        
                        # Проверяем, нужно ли отправить уведомление
                        if now <= event_start <= target_time:
                            logger.info(f"Событие '{event.get('summary', 'N/A')}' попадает в диапазон уведомлений")
                            # Проверяем, не отправляли ли уже уведомление
                            if not db.is_notification_sent(user_id, calendar_type, 
                                                          event['id'], event_start):
                                logger.info(f"Отправка уведомления о событии '{event.get('summary', 'N/A')}' пользователю {user_id}")
                                await send_notification(bot, user_id, event, calendar_type)
                                db.mark_notification_sent(user_id, calendar_type, 
                                                         event['id'], event_start)
                                events_to_notify += 1
                            else:
                                logger.info(f"Уведомление о событии '{event.get('summary', 'N/A')}' уже отправлено ранее")
                        else:
                            logger.debug(f"Событие '{event.get('summary', 'N/A')}' не попадает в диапазон (start: {event_start})")
                    
                    logger.info(f"Отправлено уведомлений для календаря {calendar_type} пользователя {user_id}: {events_to_notify}")
            
            except Exception as e:
                logger.error(f"Ошибка при обработке пользователя {user_id}: {e}", exc_info=True)
        
        logger.info("=== Завершение проверки событий ===")
    
    except Exception as e:
        logger.error(f"Ошибка при проверке событий: {e}", exc_info=True)

async def get_events_for_calendar(connection: Dict, calendar_type: str) -> List[Dict]:
    """Получение событий для календаря"""
    try:
        if calendar_type == 'google':
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from googleapiclient.errors import HttpError
            
            logger.info(f"Google Calendar: получение событий для пользователя {connection['user_id']}")
            
            # Восстанавливаем credentials
            token_data = {
                'token': connection['access_token'],
                'refresh_token': connection.get('refresh_token'),
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': Config.get_google_client_id(),
                'client_secret': Config.get_google_client_secret(),
                'scopes': Config.GOOGLE_SCOPES
            }
            
            # Проверяем наличие обязательных данных
            if not token_data['client_id']:
                logger.error("Google Calendar: Client ID не установлен")
                return []
            
            if not token_data['client_secret']:
                logger.error("Google Calendar: Client Secret не установлен")
                return []
            
            try:
                creds = Credentials.from_authorized_user_info(token_data)
            except Exception as e:
                logger.error(f"Google Calendar: ошибка при создании credentials: {e}")
                return []
            
            # Обновляем токен, если истек
            if creds.expired and creds.refresh_token:
                logger.info("Google Calendar: токен истек, обновляем...")
                try:
                    creds.refresh(Request())
                    logger.info("Google Calendar: токен успешно обновлен")
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
                except Exception as e:
                    logger.error(f"Google Calendar: ошибка при обновлении токена: {e}")
                    logger.warning("Google Calendar: возможно, нужно переподключить календарь")
                    return []
            elif creds.expired and not creds.refresh_token:
                logger.error("Google Calendar: токен истек и нет refresh_token. Нужно переподключить календарь.")
                return []
            
            time_min = datetime.utcnow()
            time_max = time_min + timedelta(days=1)
            
            try:
                events = google_cal.get_upcoming_events(creds, time_min, time_max, max_results=50)
                logger.info(f"Google Calendar: успешно получено {len(events)} событий")
                return events
            except HttpError as e:
                error_details = e.error_details if hasattr(e, 'error_details') else str(e)
                logger.error(f"Google Calendar: HttpError {e.resp.status if hasattr(e, 'resp') else 'unknown'}: {error_details}")
                
                # Специальная обработка ошибки 403
                if hasattr(e, 'resp') and e.resp.status == 403:
                    reason = error_details[0].get('reason', '') if isinstance(error_details, list) and error_details else ''
                    if 'accessNotConfigured' in str(error_details):
                        logger.error("Google Calendar: API не включен или OAuth не настроен правильно")
                        logger.error("Решение: 1) Включите Google Calendar API в Google Cloud Console")
                        logger.error("         2) Проверьте OAuth Consent Screen")
                        logger.error("         3) Переподключите календарь в боте")
                    else:
                        logger.error(f"Google Calendar: ошибка доступа (403). Причина: {reason}")
                return []
            except Exception as e:
                logger.error(f"Google Calendar: неожиданная ошибка при получении событий: {e}", exc_info=True)
                return []
        
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
        from i18n import t
        from telegram.error import TelegramError, BadRequest, Forbidden
        
        event_start = event['start']
        start_time_str = event_start.strftime('%d.%m.%Y %H:%M')
        
        title = event.get('summary', 'Event')
        location = event.get('location', '')
        description = event.get('description', '')
        if description and len(description) > 200:
            description = description[:200] + "..."
        
        message = t("event_notification", user_id, 
                   title=title,
                   start_time=start_time_str,
                   location=location if location else '-',
                   description=description if description else '-')
        
        await bot.send_message(chat_id=user_id, text=message)
        logger.info(f"Уведомление отправлено пользователю {user_id} о событии {event['id']}")
    
    except BadRequest as e:
        error_message = str(e).lower()
        if 'chat not found' in error_message or 'chat_id is empty' in error_message:
            logger.warning(f"Пользователь {user_id} не зарегистрирован в боте (никогда не отправлял /start). Пропуск уведомления.")
        else:
            logger.error(f"Ошибка BadRequest при отправке уведомления пользователю {user_id}: {e}")
    
    except Forbidden as e:
        error_message = str(e).lower()
        if 'bot was blocked by the user' in error_message:
            logger.warning(f"Пользователь {user_id} заблокировал бота. Пропуск уведомления.")
        elif 'user is deactivated' in error_message:
            logger.warning(f"Пользователь {user_id} деактивировал аккаунт. Пропуск уведомления.")
        else:
            logger.error(f"Ошибка Forbidden при отправке уведомления пользователю {user_id}: {e}")
    
    except TelegramError as e:
        logger.error(f"Ошибка Telegram API при отправке уведомления пользователю {user_id}: {e}")
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка при отправке уведомления пользователю {user_id}: {e}", exc_info=True)

