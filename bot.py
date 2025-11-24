"""Telegram бот с интерфейсом на кнопках"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from database import Database
from calendar_google import GoogleCalendar
from calendar_yandex import YandexCalendar
from config import Config
from i18n import t, get_language_name, SUPPORTED_LANGUAGES

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
google_cal = GoogleCalendar()
yandex_cal = YandexCalendar()

# Состояния для ожидания кода авторизации
user_states = {}

def get_main_menu(user_id: int):
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton(t("menu_calendars", user_id), callback_data="menu_calendars")],
        [InlineKeyboardButton(t("menu_settings", user_id), callback_data="menu_settings")],
        [InlineKeyboardButton(t("menu_help", user_id), callback_data="menu_help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_calendars_menu(user_id: int):
    """Меню управления календарями"""
    calendars = db.get_user_calendars(user_id)
    keyboard = []
    
    # Проверяем подключенные календари
    has_google = any(c['calendar_type'] == 'google' for c in calendars)
    has_yandex = any(c['calendar_type'] == 'yandex' for c in calendars)
    
    if not has_google:
        keyboard.append([InlineKeyboardButton(t("connect_google", user_id), callback_data="connect_google")])
    else:
        google_cal = next((c for c in calendars if c['calendar_type'] == 'google'), None)
        cal_name = google_cal.get('calendar_name', t("connected", user_id)) if google_cal else t("connected", user_id)
        keyboard.append([InlineKeyboardButton(
            t("google_connected", user_id, name=cal_name),
            callback_data="info_google"
        )])
        keyboard.append([InlineKeyboardButton(t("disconnect_google", user_id), callback_data="disconnect_google")])
    
    if not has_yandex:
        keyboard.append([InlineKeyboardButton(t("connect_yandex", user_id), callback_data="connect_yandex")])
    else:
        yandex_cal = next((c for c in calendars if c['calendar_type'] == 'yandex'), None)
        cal_name = yandex_cal.get('calendar_name', t("connected", user_id)) if yandex_cal else t("connected", user_id)
        keyboard.append([InlineKeyboardButton(
            t("yandex_connected", user_id, name=cal_name),
            callback_data="info_yandex"
        )])
        keyboard.append([InlineKeyboardButton(t("disconnect_yandex", user_id), callback_data="disconnect_yandex")])
    
    keyboard.append([InlineKeyboardButton(t("back_main", user_id), callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu(user_id: int):
    """Меню настроек"""
    settings = db.get_notification_settings(user_id)
    minutes = settings.get('notification_minutes', 15)
    enabled = settings.get('enabled', True)
    
    keyboard = [
        [InlineKeyboardButton(t("settings_time", user_id, minutes=minutes), callback_data="settings_time")],
        [InlineKeyboardButton(t("menu_language", user_id), callback_data="menu_language")],
        [
            InlineKeyboardButton(
                t("settings_enabled", user_id) if enabled else t("settings_disabled", user_id),
                callback_data="toggle_notifications"
            ),
            InlineKeyboardButton(t("back_main", user_id), callback_data="menu_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_time_menu(user_id: int):
    """Меню выбора времени уведомления"""
    keyboard = [
        [InlineKeyboardButton(t("time_5", user_id), callback_data="time_5")],
        [InlineKeyboardButton(t("time_10", user_id), callback_data="time_10")],
        [InlineKeyboardButton(t("time_15", user_id), callback_data="time_15")],
        [InlineKeyboardButton(t("time_30", user_id), callback_data="time_30")],
        [InlineKeyboardButton(t("time_60", user_id), callback_data="time_60")],
        [InlineKeyboardButton(t("time_120", user_id), callback_data="time_120")],
        [InlineKeyboardButton(t("back", user_id), callback_data="menu_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_language_menu(user_id: int):
    """Меню выбора языка"""
    keyboard = [
        [InlineKeyboardButton(t("language_english", user_id), callback_data="lang_en")],
        [InlineKeyboardButton(t("language_russian", user_id), callback_data="lang_ru")],
        [InlineKeyboardButton(t("language_spanish", user_id), callback_data="lang_es")],
        [InlineKeyboardButton(t("back", user_id), callback_data="menu_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    welcome_text = t("welcome", user.id, name=user.first_name)
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu(user.id))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех callback кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Главное меню
    if data == "menu_main":
        text = t("main_menu", user_id)
        await query.edit_message_text(text, reply_markup=get_main_menu(user_id))
    
    # Меню календарей
    elif data == "menu_calendars":
        calendars = db.get_user_calendars(user_id)
        if calendars:
            text = t("calendars_title", user_id)
            for cal in calendars:
                cal_type = "Google" if cal['calendar_type'] == 'google' else "Yandex"
                cal_name = cal.get('calendar_name', t("unknown", user_id))
                text += f"• {cal_type}: {cal_name}\n"
        else:
            text = t("calendars_empty", user_id)
        await query.edit_message_text(text, reply_markup=get_calendars_menu(user_id))
    
    # Подключение Google
    elif data == "connect_google":
        existing = db.get_calendar_connection(user_id, 'google')
        if existing:
            await query.answer(t("google_already_connected", user_id), show_alert=True)
            return
        
        # Передаем user_id в authorization URL для автоматической обработки в callback
        auth_url = google_cal.get_authorization_url(user_id=user_id)
        user_states[user_id] = 'waiting_google_code'
        
        keyboard = [
            [InlineKeyboardButton(t("authorize", user_id), url=auth_url)],
            [InlineKeyboardButton(t("back", user_id), callback_data="menu_calendars")]
        ]
        
        text = t("connect_google_title", user_id)
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Подключение Yandex
    elif data == "connect_yandex":
        existing = db.get_calendar_connection(user_id, 'yandex')
        if existing:
            await query.answer(t("yandex_already_connected", user_id), show_alert=True)
            return
        
        try:
            # Пересоздаем экземпляр YandexCalendar для получения актуальных настроек
            from calendar_yandex import YandexCalendar
            yandex_cal_instance = YandexCalendar()
            
            # Проверяем, что настройки заполнены
            if not yandex_cal_instance.client_id:
                await query.answer(
                    t("error_yandex_not_configured", user_id) if t("error_yandex_not_configured", user_id) != "error_yandex_not_configured" 
                    else "Yandex не настроен. Пожалуйста, заполните Yandex Client ID и Client Secret в админ-панели: Настройки → Основные настройки",
                    show_alert=True
                )
                await query.edit_message_text(
                    t("error_yandex_not_configured", user_id) if t("error_yandex_not_configured", user_id) != "error_yandex_not_configured"
                    else "❌ Yandex не настроен.\n\nПожалуйста, заполните Yandex Client ID и Client Secret в админ-панели:\nНастройки → Основные настройки",
                    reply_markup=get_calendars_menu(user_id)
                )
                return
            
            # Для Yandex также передаем user_id (если поддерживается)
            auth_url = yandex_cal_instance.get_authorization_url(user_id=user_id)
            user_states[user_id] = 'waiting_yandex_code'
            
            keyboard = [
                [InlineKeyboardButton(t("authorize", user_id), url=auth_url)],
                [InlineKeyboardButton(t("back", user_id), callback_data="menu_calendars")]
            ]
            
            text = t("connect_yandex_title", user_id)
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except ValueError as e:
            logger.error(f"Ошибка при создании URL авторизации Yandex: {e}")
            await query.answer(str(e), show_alert=True)
            await query.edit_message_text(
                f"❌ Ошибка настройки Yandex:\n\n{str(e)}\n\nПожалуйста, заполните настройки в админ-панели.",
                reply_markup=get_calendars_menu(user_id)
            )
        except Exception as e:
            logger.error(f"Ошибка при подключении Yandex: {e}")
            await query.answer(t("error_connection", user_id), show_alert=True)
            await query.edit_message_text(
                t("error_connection", user_id),
                reply_markup=get_calendars_menu(user_id)
            )
    
    # Отключение календарей
    elif data == "disconnect_google":
        db.delete_calendar_connection(user_id, 'google')
        await query.answer(t("google_disconnected_alert", user_id), show_alert=True)
        await query.edit_message_text(t("google_disconnected", user_id), reply_markup=get_calendars_menu(user_id))
    
    elif data == "disconnect_yandex":
        db.delete_calendar_connection(user_id, 'yandex')
        await query.answer(t("yandex_disconnected_alert", user_id), show_alert=True)
        await query.edit_message_text(t("yandex_disconnected", user_id), reply_markup=get_calendars_menu(user_id))
    
    # Информация о календарях
    elif data == "info_google":
        connection = db.get_calendar_connection(user_id, 'google')
        if connection:
            cal_name = connection.get('calendar_name', t("unknown", user_id))
            date = connection.get('created_at', 'N/A')[:10] if connection.get('created_at') else 'N/A'
            text = t("calendar_info_google", user_id, name=cal_name, date=date)
            keyboard = [[InlineKeyboardButton(t("back", user_id), callback_data="menu_calendars")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "info_yandex":
        connection = db.get_calendar_connection(user_id, 'yandex')
        if connection:
            cal_name = connection.get('calendar_name', t("unknown", user_id))
            date = connection.get('created_at', 'N/A')[:10] if connection.get('created_at') else 'N/A'
            text = t("calendar_info_yandex", user_id, name=cal_name, date=date)
            keyboard = [[InlineKeyboardButton(t("back", user_id), callback_data="menu_calendars")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Меню настроек
    elif data == "menu_settings":
        settings = db.get_notification_settings(user_id)
        minutes = settings.get('notification_minutes', 15)
        enabled = settings.get('enabled', True)
        status = t("settings_enabled", user_id) if enabled else t("settings_disabled", user_id)
        
        text = t("settings_title", user_id, minutes=minutes, status=status)
        await query.edit_message_text(text, reply_markup=get_settings_menu(user_id))
    
    # Выбор времени
    elif data == "settings_time":
        text = t("settings_time_menu", user_id)
        await query.edit_message_text(text, reply_markup=get_time_menu(user_id))
    
    # Установка времени
    elif data.startswith("time_"):
        minutes = int(data.split("_")[1])
        db.update_notification_settings(user_id, minutes)
        await query.answer(t("time_set_alert", user_id, minutes=minutes), show_alert=True)
        await query.edit_message_text(
            t("time_set", user_id, minutes=minutes),
            reply_markup=get_settings_menu(user_id)
        )
    
    # Переключение уведомлений
    elif data == "toggle_notifications":
        settings = db.get_notification_settings(user_id)
        new_enabled = not settings.get('enabled', True)
        db.update_notification_settings(user_id, settings.get('notification_minutes', 15), new_enabled)
        status_text = t("notifications_enabled", user_id) if new_enabled else t("notifications_disabled", user_id)
        await query.answer(t("notifications_toggled", user_id, status=status_text), show_alert=True)
        status = t("settings_enabled", user_id) if new_enabled else t("settings_disabled", user_id)
        text = t("settings_title", user_id, minutes=settings.get('notification_minutes', 15), status=status)
        await query.edit_message_text(text, reply_markup=get_settings_menu(user_id))
    
    # Помощь
    elif data == "menu_help":
        text = t("help_text", user_id)
        keyboard = [[InlineKeyboardButton(t("back_main", user_id), callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Меню выбора языка
    elif data == "menu_language":
        from i18n import get_user_language, get_language_name
        current_lang = get_user_language(user_id)
        current_name = get_language_name(current_lang)
        text = t("language_title", user_id, current=current_name)
        await query.edit_message_text(text, reply_markup=get_language_menu(user_id))
    
    # Установка языка
    elif data.startswith("lang_"):
        from i18n import set_user_language, get_language_name
        lang_code = data.split("_")[1]
        if lang_code in SUPPORTED_LANGUAGES:
            set_user_language(user_id, lang_code)
            lang_name = get_language_name(lang_code)
            await query.answer(t("language_changed", user_id, language=lang_name), show_alert=True)
            # Обновляем меню настроек с новым языком
            settings = db.get_notification_settings(user_id)
            minutes = settings.get('notification_minutes', 15)
            enabled = settings.get('enabled', True)
            status = t("settings_enabled", user_id) if enabled else t("settings_disabled", user_id)
            text = t("settings_title", user_id, minutes=minutes, status=status)
            await query.edit_message_text(text, reply_markup=get_settings_menu(user_id))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений (для кодов авторизации)"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Проверяем, ожидаем ли мы код авторизации
    if user_id in user_states:
        state = user_states[user_id]
        
        if state == 'waiting_google_code':
            try:
                credentials = google_cal.get_credentials_from_code(text)
                
                expires_at = None
                if credentials.expiry:
                    expires_at = credentials.expiry
                
                calendar_info = google_cal.get_calendar_info(credentials)
                
                db.save_calendar_connection(
                    user_id=user_id,
                    calendar_type='google',
                    access_token=credentials.token,
                    refresh_token=credentials.refresh_token,
                    token_expires_at=expires_at,
                    calendar_id=calendar_info.get('id'),
                    calendar_name=calendar_info.get('name')
                )
                
                del user_states[user_id]
                
                await update.message.reply_text(
                    t("google_success", user_id, name=calendar_info.get('name')),
                    reply_markup=get_main_menu(user_id)
                )
            except Exception as e:
                logger.error(f"Ошибка при авторизации Google: {e}")
                await update.message.reply_text(
                    t("error_connection", user_id),
                    reply_markup=get_main_menu(user_id)
                )
                del user_states[user_id]
        
        elif state == 'waiting_yandex_code':
            try:
                token_data = yandex_cal.get_token_from_code(text)
                
                if not token_data:
                    await update.message.reply_text(
                        t("error_token", user_id),
                        reply_markup=get_main_menu(user_id)
                    )
                    del user_states[user_id]
                    return
                
                calendar_info = yandex_cal.get_calendar_info(token_data['access_token'])
                
                expires_at = None
                if token_data.get('expires_in'):
                    expires_at = datetime.utcnow() + timedelta(seconds=token_data['expires_in'])
                
                db.save_calendar_connection(
                    user_id=user_id,
                    calendar_type='yandex',
                    access_token=token_data['access_token'],
                    refresh_token=token_data.get('refresh_token'),
                    token_expires_at=expires_at,
                    calendar_id=calendar_info.get('id'),
                    calendar_name=calendar_info.get('name')
                )
                
                del user_states[user_id]
                
                await update.message.reply_text(
                    t("yandex_success", user_id, name=calendar_info.get('name')),
                    reply_markup=get_main_menu(user_id)
                )
            except Exception as e:
                logger.error(f"Ошибка при авторизации Yandex: {e}")
                await update.message.reply_text(
                    t("error_connection", user_id),
                    reply_markup=get_main_menu(user_id)
                )
                del user_states[user_id]
    else:
        # Если не ожидаем код, показываем главное меню
        await update.message.reply_text(
            t("use_buttons", user_id),
            reply_markup=get_main_menu(user_id)
        )

def setup_bot():
    """Настройка и запуск бота"""
    Config.validate()
    
    token = Config.get_telegram_token()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не установлен. Установите его в админ панели или .env файле")
    
    application = Application.builder().token(token).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application
