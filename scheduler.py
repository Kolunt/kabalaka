"""Планировщик проверки событий"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Set
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
    """Проверка событий и отправка уведомлений из кэшированной БД"""
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
                
                # Получаем события из кэшированной БД
                now = datetime.utcnow()
                target_time = now + timedelta(minutes=notification_minutes)
                logger.info(f"Проверка событий между {now} и {target_time}")
                
                # Получаем события из БД для этого временного диапазона
                events = db.get_events_for_notification(user_id, now, target_time)
                logger.info(f"Найдено {len(events)} событий в БД для пользователя {user_id} в диапазоне уведомлений")
                
                events_to_notify = 0
                for event in events:
                    event_start = event['start']
                    calendar_type = event['calendar_type']
                    event_id = event['event_id']
                    
                    logger.debug(f"Событие: {event.get('summary', 'N/A')} в {event_start}")
                    
                    # Проверяем, нужно ли отправить уведомление
                    if now <= event_start <= target_time:
                        logger.info(f"Событие '{event.get('summary', 'N/A')}' попадает в диапазон уведомлений")
                        # Проверяем, не отправляли ли уже уведомление
                        if not db.is_notification_sent(user_id, calendar_type, event_id, event_start):
                            logger.info(f"Отправка уведомления о событии '{event.get('summary', 'N/A')}' пользователю {user_id}")
                            # Преобразуем формат события для совместимости с send_notification
                            event_dict = {
                                'id': event_id,
                                'summary': event.get('summary'),
                                'description': event.get('description'),
                                'location': event.get('location'),
                                'start': event_start,
                                'end': event.get('end'),
                                'htmlLink': event.get('html_link')
                            }
                            await send_notification(bot, user_id, event_dict, calendar_type)
                            db.mark_notification_sent(user_id, calendar_type, event_id, event_start)
                            events_to_notify += 1
                        else:
                            logger.info(f"Уведомление о событии '{event.get('summary', 'N/A')}' уже отправлено ранее")
                    else:
                        logger.debug(f"Событие '{event.get('summary', 'N/A')}' не попадает в диапазон (start: {event_start})")
                
                logger.info(f"Отправлено уведомлений для пользователя {user_id}: {events_to_notify}")
            
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
            
            # Используем переданные time_min и time_max, если они есть
            if 'time_min' not in connection or connection.get('time_min') is None:
                time_min = datetime.utcnow() - timedelta(days=30)
            else:
                time_min = connection['time_min']
            
            if 'time_max' not in connection or connection.get('time_max') is None:
                time_max = datetime.utcnow() + timedelta(days=90)
            else:
                time_max = connection['time_max']
            
            try:
                # Увеличиваем max_results для синхронизации всех событий
                max_results = connection.get('max_results', 2500)  # Google Calendar API limit
                events = google_cal.get_upcoming_events(creds, time_min, time_max, max_results=max_results)
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
            
            # Используем переданные time_min и time_max, если они есть
            if 'time_min' not in connection or connection.get('time_min') is None:
                time_min = datetime.utcnow() - timedelta(days=30)
            else:
                time_min = connection['time_min']
            
            if 'time_max' not in connection or connection.get('time_max') is None:
                time_max = datetime.utcnow() + timedelta(days=90)
            else:
                time_max = connection['time_max']
            
            max_results = connection.get('max_results', 1000)  # Yandex может иметь другие лимиты
            return yandex_cal.get_upcoming_events(access_token, time_min, time_max, max_results=max_results)
        
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

async def sync_events_from_calendars():
    """Синхронизация событий из календарей в базу данных"""
    try:
        logger.info("=== Начало синхронизации событий ===")
        active_users = db.get_all_active_users()
        logger.info(f"Найдено активных пользователей: {len(active_users)}")
        
        if not active_users:
            logger.info("Нет активных пользователей с подключенными календарями")
            return
        
        total_synced = 0
        total_deleted = 0
        
        for user_id in active_users:
            try:
                logger.info(f"Синхронизация событий для пользователя {user_id}")
                calendars = db.get_user_calendars(user_id)
                
                for cal_info in calendars:
                    calendar_type = cal_info['calendar_type']
                    logger.info(f"Синхронизация календаря {calendar_type} для пользователя {user_id}")
                    
                    connection = db.get_calendar_connection(user_id, calendar_type)
                    if not connection:
                        logger.warning(f"Подключение {calendar_type} не найдено для пользователя {user_id}")
                        continue
                    
                    # Получаем события из календаря (прошедшие и будущие)
                    # Берем широкий диапазон: от 30 дней назад до 90 дней вперед
                    time_min = datetime.utcnow() - timedelta(days=30)
                    time_max = datetime.utcnow() + timedelta(days=90)
                    
                    connection['user_id'] = user_id
                    connection['time_min'] = time_min
                    connection['time_max'] = time_max
                    connection['max_results'] = 2500  # Максимум для синхронизации
                    events = await get_events_for_calendar(connection, calendar_type)
                    logger.info(f"Получено {len(events)} событий из {calendar_type} для пользователя {user_id}")
                    
                    # Получаем текущие event_id из БД для этого календаря
                    existing_events = db.get_cached_events(user_id, calendar_type, time_min, time_max)
                    existing_event_ids: Set[tuple] = set()
                    for event in existing_events:
                        event_id = event.get('event_id')
                        start_time = event.get('start_time')
                        if isinstance(start_time, str):
                            start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        elif hasattr(start_time, 'isoformat'):
                            pass  # Уже datetime
                        else:
                            continue
                        existing_event_ids.add((event_id, start_time))
                    
                    # Сохраняем/обновляем события из календаря
                    current_event_ids: Set[tuple] = set()
                    for event in events:
                        event_id = event.get('id')
                        start_time = event.get('start')
                        current_event_ids.add((event_id, start_time))
                        
                        # Сохраняем или обновляем событие
                        db.save_or_update_event(
                            user_id=user_id,
                            calendar_type=calendar_type,
                            event_id=event_id,
                            summary=event.get('summary'),
                            description=event.get('description'),
                            location=event.get('location'),
                            start_time=start_time,
                            end_time=event.get('end'),
                            html_link=event.get('htmlLink')
                        )
                        total_synced += 1
                    
                    # Удаляем старые события (более 7 дней назад)
                    deleted = db.delete_old_events(user_id, calendar_type, datetime.utcnow() - timedelta(days=7))
                    total_deleted += deleted
                    
                    logger.info(f"Синхронизировано {len(events)} событий для календаря {calendar_type} пользователя {user_id}")
            
            except Exception as e:
                logger.error(f"Ошибка при синхронизации событий для пользователя {user_id}: {e}", exc_info=True)
        
        logger.info(f"=== Синхронизация завершена: добавлено/обновлено {total_synced}, удалено {total_deleted} ===")
    
    except Exception as e:
        logger.error(f"Ошибка при синхронизации событий: {e}", exc_info=True)

