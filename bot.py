"""Telegram бот с интерфейсом на кнопках"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from database import Database
from calendar_google import GoogleCalendar
from calendar_yandex import YandexCalendar
from config import Config

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

def get_main_menu():
    """Главное меню"""
    keyboard = [
        [InlineKeyboardButton("📅 Мои календари", callback_data="menu_calendars")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data="menu_help")]
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
        keyboard.append([InlineKeyboardButton("➕ Подключить Google Calendar", callback_data="connect_google")])
    else:
        google_cal = next((c for c in calendars if c['calendar_type'] == 'google'), None)
        keyboard.append([InlineKeyboardButton(
            f"✅ Google: {google_cal.get('calendar_name', 'Подключен')}",
            callback_data="info_google"
        )])
        keyboard.append([InlineKeyboardButton("❌ Отключить Google", callback_data="disconnect_google")])
    
    if not has_yandex:
        keyboard.append([InlineKeyboardButton("➕ Подключить Yandex Calendar", callback_data="connect_yandex")])
    else:
        yandex_cal = next((c for c in calendars if c['calendar_type'] == 'yandex'), None)
        keyboard.append([InlineKeyboardButton(
            f"✅ Yandex: {yandex_cal.get('calendar_name', 'Подключен')}",
            callback_data="info_yandex"
        )])
        keyboard.append([InlineKeyboardButton("❌ Отключить Yandex", callback_data="disconnect_yandex")])
    
    keyboard.append([InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")])
    return InlineKeyboardMarkup(keyboard)

def get_settings_menu(user_id: int):
    """Меню настроек"""
    settings = db.get_notification_settings(user_id)
    minutes = settings.get('notification_minutes', 15)
    enabled = settings.get('enabled', True)
    
    keyboard = [
        [InlineKeyboardButton(f"⏰ Время уведомления: {minutes} мин", callback_data="settings_time")],
        [
            InlineKeyboardButton("✅ Включено" if enabled else "❌ Выключено", callback_data="toggle_notifications"),
            InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_time_menu():
    """Меню выбора времени уведомления"""
    keyboard = [
        [InlineKeyboardButton("5 минут", callback_data="time_5")],
        [InlineKeyboardButton("10 минут", callback_data="time_10")],
        [InlineKeyboardButton("15 минут", callback_data="time_15")],
        [InlineKeyboardButton("30 минут", callback_data="time_30")],
        [InlineKeyboardButton("60 минут", callback_data="time_60")],
        [InlineKeyboardButton("120 минут", callback_data="time_120")],
        [InlineKeyboardButton("🔙 Назад", callback_data="menu_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name)
    
    welcome_text = (
        f"Привет, {user.first_name}! 👋\n\n"
        "Я помогу тебе получать уведомления о событиях из твоих календарей.\n\n"
        "Выберите действие:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_menu())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех callback кнопок"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Главное меню
    if data == "menu_main":
        text = "Главное меню. Выберите действие:"
        await query.edit_message_text(text, reply_markup=get_main_menu())
    
    # Меню календарей
    elif data == "menu_calendars":
        calendars = db.get_user_calendars(user_id)
        if calendars:
            text = "📅 Ваши календари:\n\n"
            for cal in calendars:
                cal_type = "Google" if cal['calendar_type'] == 'google' else "Yandex"
                text += f"• {cal_type}: {cal.get('calendar_name', 'Неизвестно')}\n"
        else:
            text = "📅 У вас пока нет подключенных календарей.\n\nВыберите календарь для подключения:"
        await query.edit_message_text(text, reply_markup=get_calendars_menu(user_id))
    
    # Подключение Google
    elif data == "connect_google":
        existing = db.get_calendar_connection(user_id, 'google')
        if existing:
            await query.answer("Google Calendar уже подключен!", show_alert=True)
            return
        
        auth_url = google_cal.get_authorization_url()
        user_states[user_id] = 'waiting_google_code'
        
        keyboard = [
            [InlineKeyboardButton("🔗 Авторизоваться", url=auth_url)],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_calendars")]
        ]
        
        text = (
            "🔗 Подключение Google Calendar\n\n"
            "1. Нажмите кнопку 'Авторизоваться'\n"
            "2. Разрешите доступ к календарю\n"
            "3. Скопируйте код авторизации\n"
            "4. Отправьте его мне в следующем сообщении"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Подключение Yandex
    elif data == "connect_yandex":
        existing = db.get_calendar_connection(user_id, 'yandex')
        if existing:
            await query.answer("Yandex Calendar уже подключен!", show_alert=True)
            return
        
        auth_url = yandex_cal.get_authorization_url()
        user_states[user_id] = 'waiting_yandex_code'
        
        keyboard = [
            [InlineKeyboardButton("🔗 Авторизоваться", url=auth_url)],
            [InlineKeyboardButton("🔙 Назад", callback_data="menu_calendars")]
        ]
        
        text = (
            "🔗 Подключение Yandex Calendar\n\n"
            "1. Нажмите кнопку 'Авторизоваться'\n"
            "2. Разрешите доступ к календарю\n"
            "3. Скопируйте код авторизации\n"
            "4. Отправьте его мне в следующем сообщении"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Отключение календарей
    elif data == "disconnect_google":
        db.delete_calendar_connection(user_id, 'google')
        await query.answer("Google Calendar отключен!", show_alert=True)
        await query.edit_message_text("✅ Google Calendar отключен", reply_markup=get_calendars_menu(user_id))
    
    elif data == "disconnect_yandex":
        db.delete_calendar_connection(user_id, 'yandex')
        await query.answer("Yandex Calendar отключен!", show_alert=True)
        await query.edit_message_text("✅ Yandex Calendar отключен", reply_markup=get_calendars_menu(user_id))
    
    # Информация о календарях
    elif data == "info_google":
        connection = db.get_calendar_connection(user_id, 'google')
        if connection:
            text = (
                f"📅 Google Calendar\n\n"
                f"Название: {connection.get('calendar_name', 'Неизвестно')}\n"
                f"Подключен: {connection.get('created_at', 'N/A')[:10] if connection.get('created_at') else 'N/A'}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_calendars")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "info_yandex":
        connection = db.get_calendar_connection(user_id, 'yandex')
        if connection:
            text = (
                f"📅 Yandex Calendar\n\n"
                f"Название: {connection.get('calendar_name', 'Неизвестно')}\n"
                f"Подключен: {connection.get('created_at', 'N/A')[:10] if connection.get('created_at') else 'N/A'}"
            )
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="menu_calendars")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    # Меню настроек
    elif data == "menu_settings":
        settings = db.get_notification_settings(user_id)
        minutes = settings.get('notification_minutes', 15)
        enabled = settings.get('enabled', True)
        
        text = (
            f"⚙️ Настройки уведомлений\n\n"
            f"Время уведомления: {minutes} минут до события\n"
            f"Статус: {'✅ Включено' if enabled else '❌ Выключено'}\n\n"
            f"Выберите параметр для изменения:"
        )
        await query.edit_message_text(text, reply_markup=get_settings_menu(user_id))
    
    # Выбор времени
    elif data == "settings_time":
        text = "⏰ Выберите время уведомления до начала события:"
        await query.edit_message_text(text, reply_markup=get_time_menu())
    
    # Установка времени
    elif data.startswith("time_"):
        minutes = int(data.split("_")[1])
        db.update_notification_settings(user_id, minutes)
        await query.answer(f"Время уведомления установлено: {minutes} минут", show_alert=True)
        await query.edit_message_text(
            f"✅ Время уведомления установлено: {minutes} минут",
            reply_markup=get_settings_menu(user_id)
        )
    
    # Переключение уведомлений
    elif data == "toggle_notifications":
        settings = db.get_notification_settings(user_id)
        new_enabled = not settings.get('enabled', True)
        db.update_notification_settings(user_id, settings.get('notification_minutes', 15), new_enabled)
        status = "включены" if new_enabled else "выключены"
        await query.answer(f"Уведомления {status}!", show_alert=True)
        await query.edit_message_text(
            f"⚙️ Настройки уведомлений\n\n"
            f"Время уведомления: {settings.get('notification_minutes', 15)} минут до события\n"
            f"Статус: {'✅ Включено' if new_enabled else '❌ Выключено'}\n\n"
            f"Выберите параметр для изменения:",
            reply_markup=get_settings_menu(user_id)
        )
    
    # Помощь
    elif data == "menu_help":
        text = (
            "📚 Помощь\n\n"
            "🔗 Подключение календарей:\n"
            "• Выберите 'Мои календари'\n"
            "• Нажмите 'Подключить' для нужного календаря\n"
            "• Авторизуйтесь и отправьте код\n\n"
            "⚙️ Настройки:\n"
            "• Выберите время уведомления (5-120 минут)\n"
            "• Включите/выключите уведомления\n\n"
            "Бот автоматически проверяет события и отправляет уведомления "
            "за указанное время до начала события."
        )
        keyboard = [[InlineKeyboardButton("🔙 Главное меню", callback_data="menu_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

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
                    f"✅ Google Calendar успешно подключен!\n"
                    f"Календарь: {calendar_info.get('name')}",
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                logger.error(f"Ошибка при авторизации Google: {e}")
                await update.message.reply_text(
                    "❌ Ошибка при подключении. Проверьте код и попробуйте снова.\n"
                    "Используйте меню для повторной попытки.",
                    reply_markup=get_main_menu()
                )
                del user_states[user_id]
        
        elif state == 'waiting_yandex_code':
            try:
                token_data = yandex_cal.get_token_from_code(text)
                
                if not token_data:
                    await update.message.reply_text(
                        "❌ Ошибка при получении токена. Проверьте код и попробуйте снова.",
                        reply_markup=get_main_menu()
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
                    f"✅ Yandex Calendar успешно подключен!\n"
                    f"Календарь: {calendar_info.get('name')}",
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                logger.error(f"Ошибка при авторизации Yandex: {e}")
                await update.message.reply_text(
                    "❌ Ошибка при подключении. Проверьте код и попробуйте снова.\n"
                    "Используйте меню для повторной попытки.",
                    reply_markup=get_main_menu()
                )
                del user_states[user_id]
    else:
        # Если не ожидаем код, показываем главное меню
        await update.message.reply_text(
            "Используйте кнопки для управления ботом:",
            reply_markup=get_main_menu()
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
