"""Flask приложение для PythonAnywhere"""
from flask import Flask, request, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
import logging
from telegram import Bot
from bot import setup_bot
from scheduler import check_and_notify_events, sync_events_from_calendars
from database import Database
from calendar_google import GoogleCalendar
from calendar_yandex import YandexCalendar
from config import Config
from admin_panel import admin_bp
from i18n import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = Config.FLASK_SECRET_KEY

# Регистрация админ панели
app.register_blueprint(admin_bp)

db = Database()
google_cal = GoogleCalendar()
yandex_cal = YandexCalendar()

# Настройка планировщика
# На PythonAnywhere лучше использовать Scheduled tasks вместо BackgroundScheduler
scheduler = None
try:
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Получаем настройки из БД или .env
    check_interval = Config.CHECK_INTERVAL_MINUTES
    try:
        db_setting = db.get_system_setting('check_interval_minutes')
        if db_setting:
            check_interval = int(db_setting)
    except:
        pass
    
    scheduler_enabled = True
    try:
        enabled_str = db.get_system_setting('scheduler_enabled')
        if enabled_str:
            scheduler_enabled = enabled_str != 'false'
    except:
        pass
    
    # Добавляем задачу проверки событий, если планировщик включен
    if scheduler_enabled:
        scheduler.add_job(
            func=lambda: asyncio.run(check_and_notify_events()),
            trigger=IntervalTrigger(minutes=check_interval),
            id='check_events',
            name='Проверка событий календарей',
            replace_existing=True
        )
        logger.info(f"Планировщик запущен с интервалом {check_interval} минут")
    else:
        logger.info("Планировщик отключен в настройках")
    
    # Добавляем задачу проверки отложенных рассылок
    from broadcast_sender import send_broadcast
    scheduler.add_job(
        func=lambda: process_pending_broadcasts(),
        trigger=IntervalTrigger(minutes=1),  # Проверяем каждую минуту
        id='check_broadcasts',
        name='Проверка отложенных рассылок',
        replace_existing=True
    )
    logger.info("Планировщик рассылок запущен")
    
except Exception as e:
    logger.warning(f"Не удалось запустить планировщик: {e}. Используйте Scheduled tasks на PythonAnywhere.")

def process_pending_broadcasts():
    """Обработка отложенных рассылок"""
    try:
        from broadcast_sender import send_broadcast
        pending = db.get_pending_broadcasts()
        for broadcast in pending:
            logger.info(f"Запуск отложенной рассылки {broadcast['id']}")
            send_broadcast(broadcast['id'])
    except Exception as e:
        logger.error(f"Ошибка при обработке отложенных рассылок: {e}")

@app.route('/')
def index():
    """Главная страница"""
    return redirect(url_for('admin.login'))

@app.route('/callback/google')
def google_callback():
    """Callback для Google OAuth - автоматическая обработка"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        error_message = f"Ошибка авторизации: {error}"
        logger.error(error_message)
        return f"""
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка авторизации</h1>
                <p>{error_message}</p>
                <p>Попробуйте снова через бота в Telegram.</p>
            </body>
        </html>
        """, 400
    
    if not code:
        return """
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка</h1>
                <p>Код авторизации не получен</p>
            </body>
        </html>
        """, 400
    
    # Извлекаем user_id из state
    user_id = None
    if state:
        try:
            user_id = int(state)
        except ValueError:
            logger.warning(f"Неверный формат state: {state}")
    
    if not user_id:
        return """
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка</h1>
                <p>Не удалось определить пользователя. Пожалуйста, начните авторизацию через бота в Telegram.</p>
            </body>
        </html>
        """, 400
    
    # Автоматически обрабатываем код
    try:
        credentials = google_cal.get_credentials_from_code(code)
        
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
        
        # Отправляем уведомление пользователю через Telegram
        try:
            token = Config.get_telegram_token()
            if token:
                bot = Bot(token=token)
                # Используем asyncio для отправки сообщения
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    bot.send_message(
                        chat_id=user_id,
                        text=t("google_success", user_id, name=calendar_info.get('name'))
                    )
                )
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
        
        return """
        <html>
            <head>
                <meta charset="utf-8">
                <title>Авторизация успешна</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .success { color: #27ae60; }
                </style>
            </head>
            <body>
                <h1 class="success">✅ Авторизация успешна!</h1>
                <p>Google Calendar успешно подключен.</p>
                <p>Вы можете закрыть это окно и вернуться в Telegram.</p>
            </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кода авторизации Google для пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Отправляем сообщение об ошибке пользователю
        try:
            token = Config.get_telegram_token()
            if token:
                bot = Bot(token=token)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    bot.send_message(
                        chat_id=user_id,
                        text=t("error_connection", user_id)
                    )
                )
                loop.close()
        except Exception as e2:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e2}")
        
        return f"""
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка</h1>
                <p>Не удалось подключить Google Calendar. Попробуйте снова через бота в Telegram.</p>
                <p>Ошибка: {str(e)}</p>
            </body>
        </html>
        """, 500

@app.route('/callback/yandex')
def yandex_callback():
    """Callback для Yandex OAuth - автоматическая обработка"""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    
    if error:
        error_message = f"Ошибка авторизации: {error}"
        logger.error(error_message)
        return f"""
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка авторизации</h1>
                <p>{error_message}</p>
                <p>Попробуйте снова через бота в Telegram.</p>
            </body>
        </html>
        """, 400
    
    if not code:
        return """
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка</h1>
                <p>Код авторизации не получен</p>
            </body>
        </html>
        """, 400
    
    # Извлекаем user_id из state
    user_id = None
    if state:
        try:
            user_id = int(state)
        except ValueError:
            logger.warning(f"Неверный формат state: {state}")
    
    if not user_id:
        return """
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка</h1>
                <p>Не удалось определить пользователя. Пожалуйста, начните авторизацию через бота в Telegram.</p>
            </body>
        </html>
        """, 400
    
    # Автоматически обрабатываем код
    try:
        token_data = yandex_cal.get_token_from_code(code)
        
        if not token_data:
            raise Exception("Не удалось получить токен от Yandex")
        
        calendar_info = yandex_cal.get_calendar_info(token_data['access_token'])
        
        expires_at = None
        if token_data.get('expires_in'):
            from datetime import datetime, timedelta
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
        
        # Отправляем уведомление пользователю через Telegram
        try:
            token = Config.get_telegram_token()
            if token:
                bot = Bot(token=token)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    bot.send_message(
                        chat_id=user_id,
                        text=t("yandex_success", user_id, name=calendar_info.get('name'))
                    )
                )
                loop.close()
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
        
        return """
        <html>
            <head>
                <meta charset="utf-8">
                <title>Авторизация успешна</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .success { color: #27ae60; }
                </style>
            </head>
            <body>
                <h1 class="success">✅ Авторизация успешна!</h1>
                <p>Yandex Calendar успешно подключен.</p>
                <p>Вы можете закрыть это окно и вернуться в Telegram.</p>
            </body>
        </html>
        """
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кода авторизации Yandex для пользователя {user_id}: {e}")
        import traceback
        traceback.print_exc()
        
        # Отправляем сообщение об ошибке пользователю
        try:
            token = Config.get_telegram_token()
            if token:
                bot = Bot(token=token)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(
                    bot.send_message(
                        chat_id=user_id,
                        text=t("error_connection", user_id)
                    )
                )
                loop.close()
        except Exception as e2:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e2}")
        
        return f"""
        <html>
            <head><meta charset="utf-8"></head>
            <body>
                <h1>Ошибка</h1>
                <p>Не удалось подключить Yandex Calendar. Попробуйте снова через бота в Telegram.</p>
                <p>Ошибка: {str(e)}</p>
            </body>
        </html>
        """, 500

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для Telegram (если используется)"""
    # Если используете webhook вместо polling
    # Здесь будет обработка обновлений от Telegram
    # Для использования webhook нужно:
    # 1. Настроить URL в BotFather: https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://yourusername.pythonanywhere.com/webhook
    # 2. Реализовать обработку обновлений
    return "OK", 200

@app.route('/health')
def health():
    """Health check endpoint"""
    return {"status": "ok"}, 200

@app.route('/cron/wake')
def cron_wake():
    """Endpoint для пробуждения Web app (вызывается внешним cron-сервисом)"""
    logger.info("Web app пробужден через /cron/wake")
    return {"status": "awake", "message": "Web app активен"}, 200

@app.route('/cron/sync-events')
def cron_sync_events():
    """Endpoint для синхронизации событий из календарей в БД (вызывается внешним cron-сервисом)"""
    try:
        logger.info("=" * 50)
        logger.info("Запуск синхронизации событий через /cron/sync-events")
        logger.info("=" * 50)
        asyncio.run(sync_events_from_calendars())
        logger.info("Синхронизация событий завершена успешно")
        return {"status": "success", "message": "Синхронизация событий выполнена"}, 200
    except Exception as e:
        logger.error(f"Ошибка при синхронизации событий: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

@app.route('/cron/check-events')
def cron_check_events():
    """Endpoint для проверки событий и отправки уведомлений (вызывается внешним cron-сервисом)"""
    try:
        logger.info("=" * 50)
        logger.info("Запуск проверки событий через /cron/check-events")
        logger.info("=" * 50)
        asyncio.run(check_and_notify_events())
        logger.info("Проверка событий завершена успешно")
        return {"status": "success", "message": "Проверка событий выполнена"}, 200
    except Exception as e:
        logger.error(f"Ошибка при проверке событий: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

@app.route('/test/check-events')
def test_check_events():
    """Тестовый endpoint для проверки событий (для отладки)"""
    try:
        logger.info("=" * 50)
        logger.info("ТЕСТОВЫЙ запуск проверки событий")
        logger.info("=" * 50)
        asyncio.run(check_and_notify_events())
        logger.info("Тестовая проверка событий завершена")
        return {"status": "success", "message": "Тестовая проверка событий выполнена. Проверьте логи."}, 200
    except Exception as e:
        logger.error(f"Ошибка при тестовой проверке событий: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

@app.route('/cron/check-broadcasts')
def cron_check_broadcasts():
    """Endpoint для проверки отложенных рассылок (вызывается внешним cron-сервисом)"""
    try:
        logger.info("Запуск проверки рассылок через /cron/check-broadcasts")
        process_pending_broadcasts()
        return {"status": "success", "message": "Проверка рассылок выполнена"}, 200
    except Exception as e:
        logger.error(f"Ошибка при проверке рассылок: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/cron/run-bot')
def cron_run_bot():
    """Endpoint для запуска бота на обработку накопившихся сообщений (вызывается внешним cron-сервисом)"""
    try:
        logger.info("Запуск обработки обновлений через /cron/run-bot")
        
        # Используем process_updates_once вместо бесконечного polling
        # Это обработает накопившиеся обновления и завершится
        import threading
        from process_updates import process_updates_once
        
        def process_updates_thread():
            try:
                asyncio.run(process_updates_once())
            except Exception as e:
                logger.error(f"Ошибка при обработке обновлений: {e}", exc_info=True)
        
        thread = threading.Thread(target=process_updates_thread)
        thread.daemon = True
        thread.start()
        
        return {"status": "started", "message": "Обработка обновлений запущена"}, 200
    except Exception as e:
        logger.error(f"Ошибка при запуске обработки обновлений: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}, 500

@app.route('/cron/run-all')
def cron_run_all():
    """Endpoint для запуска всех задач (вызывается внешним cron-сервисом)"""
    try:
        logger.info("Запуск всех задач через /cron/run-all")
        
        # Синхронизация событий
        try:
            asyncio.run(sync_events_from_calendars())
        except Exception as e:
            logger.error(f"Ошибка при синхронизации событий: {e}")
        
        # Проверка событий и отправка уведомлений
        try:
            asyncio.run(check_and_notify_events())
        except Exception as e:
            logger.error(f"Ошибка при проверке событий: {e}")
        
        # Проверка рассылок
        try:
            process_pending_broadcasts()
        except Exception as e:
            logger.error(f"Ошибка при проверке рассылок: {e}")
        
        return {
            "status": "success", 
            "message": "Все задачи выполнены",
            "tasks": ["sync-events", "check-events", "check-broadcasts"]
        }, 200
    except Exception as e:
        logger.error(f"Ошибка при выполнении задач: {e}")
        return {"status": "error", "message": str(e)}, 500

# Примечание: 
# - На платном тарифе PythonAnywhere: бот запускается через Always-on task используя run_bot.py
# - На бесплатном тарифе: используйте внешние cron-сервисы для вызова /cron/* endpoints

if __name__ == '__main__':
    # Локальный запуск Flask приложения
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=True
    )

