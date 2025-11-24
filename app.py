"""Flask приложение для PythonAnywhere"""
from flask import Flask, request, redirect, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio
import logging
from bot import setup_bot
from scheduler import check_and_notify_events
from database import Database
from calendar_google import GoogleCalendar
from calendar_yandex import YandexCalendar
from config import Config
from admin_panel import admin_bp

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
try:
    scheduler = BackgroundScheduler()
    scheduler.start()
    
    # Добавляем задачу проверки событий
    scheduler.add_job(
        func=lambda: asyncio.run(check_and_notify_events()),
        trigger=IntervalTrigger(minutes=Config.CHECK_INTERVAL_MINUTES),
        id='check_events',
        name='Проверка событий календарей',
        replace_existing=True
    )
    logger.info("Планировщик запущен")
except Exception as e:
    logger.warning(f"Не удалось запустить планировщик: {e}. Используйте Scheduled tasks на PythonAnywhere.")

@app.route('/')
def index():
    """Главная страница"""
    return redirect(url_for('admin.login'))

@app.route('/callback/google')
def google_callback():
    """Callback для Google OAuth"""
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code:
        return "Ошибка: код авторизации не получен", 400
    
    # Здесь нужно сохранить код и связать его с пользователем
    # В реальном приложении нужно использовать state для идентификации пользователя
    return f"""
    <html>
        <body>
            <h1>Авторизация успешна!</h1>
            <p>Код авторизации: {code}</p>
            <p>Отправьте этот код боту командой: /auth_google {code}</p>
        </body>
    </html>
    """

@app.route('/callback/yandex')
def yandex_callback():
    """Callback для Yandex OAuth"""
    code = request.args.get('code')
    
    if not code:
        return "Ошибка: код авторизации не получен", 400
    
    return f"""
    <html>
        <body>
            <h1>Авторизация успешна!</h1>
            <p>Код авторизации: {code}</p>
            <p>Отправьте этот код боту командой: /auth_yandex {code}</p>
        </body>
    </html>
    """

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

# Примечание: На PythonAnywhere бот должен запускаться отдельно через Always-on task
# используя run_bot.py, а Flask приложение запускается автоматически через Web app

if __name__ == '__main__':
    # Локальный запуск Flask приложения
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=True
    )

