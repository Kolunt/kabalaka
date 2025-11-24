"""Админ панель для управления системой"""
from flask import Blueprint, render_template_string, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import hashlib
import logging
import asyncio
from database import Database
from config import Config
from bot_manager import check_bot_connection, is_bot_running, get_bot_pid, restart_bot

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
db = Database()

# HTML шаблоны
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Админ панель - Вход</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 100px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .login-form {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
        }
        input[type="text"], input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            width: 100%;
            padding: 12px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background: #0056b3;
        }
        .error {
            color: red;
            margin-top: 10px;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="login-form">
        <h1>🔐 Вход в админ панель</h1>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="form-group">
                <label>Имя пользователя:</label>
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Пароль:</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit">Войти</button>
        </form>
    </div>
</body>
</html>
"""

# Базовый шаблон с навигацией
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{% block title %}Админ панель{% endblock %}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            background: #f5f5f5;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .header-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            display: inline-block;
            margin: 0;
        }
        .logout {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            background: #e74c3c;
            border-radius: 4px;
        }
        .logout:hover {
            background: #c0392b;
        }
        .nav {
            background: #34495e;
            padding: 0;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .nav-content {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
        }
        .nav a {
            color: white;
            text-decoration: none;
            padding: 15px 20px;
            display: block;
            transition: background 0.3s;
        }
        .nav a:hover {
            background: #2c3e50;
        }
        .nav a.active {
            background: #2c3e50;
            border-bottom: 3px solid #3498db;
        }
        .container {
            max-width: 1200px;
            margin: 20px auto;
            padding: 0 20px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-card h3 {
            color: #7f8c8d;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
        }
        .section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .section h2 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f8f9fa;
            font-weight: bold;
            color: #2c3e50;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .badge-success {
            background: #27ae60;
            color: white;
        }
        .badge-info {
            background: #3498db;
            color: white;
        }
        .user-link {
            color: #3498db;
            text-decoration: none;
        }
        .user-link:hover {
            text-decoration: underline;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: #2c3e50;
            font-weight: bold;
        }
        .form-group input[type="text"],
        .form-group input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        .form-group input:focus {
            outline: none;
            border-color: #3498db;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-primary:hover {
            background: #2980b9;
        }
        .alert {
            padding: 15px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>Админ панель - Calendar Alarm Bot</h1>
            <a href="{{ url_for('admin.logout') }}" class="logout">Выйти</a>
        </div>
    </div>
    <div class="nav">
        <div class="nav-content">
            <a href="{{ url_for('admin.dashboard') }}" class="{% if active_page == 'dashboard' %}active{% endif %}">Дашборд</a>
            <a href="{{ url_for('admin.users') }}" class="{% if active_page == 'users' %}active{% endif %}">Пользователи</a>
            <a href="{{ url_for('admin.settings') }}" class="{% if active_page == 'settings' %}active{% endif %}">Настройки</a>
        </div>
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

DASHBOARD_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="stats">
    <div class="stat-card">
        <h3>Всего пользователей</h3>
        <div class="value">{{ stats.total_users }}</div>
    </div>
    <div class="stat-card">
        <h3>Активных пользователей</h3>
        <div class="value">{{ stats.active_users }}</div>
    </div>
    <div class="stat-card">
        <h3>Подключенных календарей</h3>
        <div class="value">{{ stats.total_calendars }}</div>
    </div>
    <div class="stat-card">
        <h3>Уведомлений (24ч)</h3>
        <div class="value">{{ stats.notifications_24h }}</div>
    </div>
</div>

<div class="section">
    <h2>Статистика</h2>
    <table>
        <tr>
            <th>Метрика</th>
            <th>Значение</th>
        </tr>
        <tr>
            <td>Google календари</td>
            <td><span class="badge badge-info">{{ stats.google_calendars }}</span></td>
        </tr>
        <tr>
            <td>Yandex календари</td>
            <td><span class="badge badge-info">{{ stats.yandex_calendars }}</span></td>
        </tr>
        <tr>
            <td>Всего уведомлений</td>
            <td><span class="badge badge-success">{{ stats.total_notifications }}</span></td>
        </tr>
    </table>
</div>
{% endblock %}
''')

USERS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="section">
    <h2>Пользователи</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Имя</th>
            <th>Username</th>
            <th>Календари</th>
            <th>Уведомлений</th>
            <th>Дата регистрации</th>
            <th>Действия</th>
        </tr>
        {% for user in users %}
        <tr>
            <td>{{ user.user_id }}</td>
            <td>{{ user.first_name or 'N/A' }}</td>
            <td>@{{ user.username or 'N/A' }}</td>
            <td><span class="badge badge-info">{{ user.calendar_count }}</span></td>
            <td><span class="badge badge-success">{{ user.notification_count }}</span></td>
            <td>{{ user.created_at[:10] if user.created_at else 'N/A' }}</td>
            <td><a href="{{ url_for('admin.user_details', user_id=user.user_id) }}" class="user-link">Подробнее</a></td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
''')

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template_string(LOGIN_TEMPLATE, error='Заполните все поля')
        
        admin = db.get_admin(username)
        if admin and admin['password_hash'] == hash_password(password):
            session['admin_logged_in'] = True
            session['admin_username'] = username
            return redirect(url_for('admin.dashboard'))
        else:
            return render_template_string(LOGIN_TEMPLATE, error='Неверное имя пользователя или пароль')
    
    return render_template_string(LOGIN_TEMPLATE)

@admin_bp.route('/logout')
def logout():
    """Выход из админ панели"""
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@login_required
def dashboard():
    """Главная страница админ панели (дашборд)"""
    stats = db.get_statistics()
    return render_template_string(DASHBOARD_TEMPLATE, stats=stats, active_page='dashboard')

@admin_bp.route('/users')
@login_required
def users():
    """Страница со списком пользователей"""
    users_list = db.get_all_users()
    return render_template_string(USERS_TEMPLATE, users=users_list, active_page='users')

SETTINGS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="section">
    <h2>Настройки системы</h2>
    {% if message %}
    <div class="alert alert-{{ message_type or 'success' }}">{{ message }}</div>
    {% endif %}
    <form method="POST" action="{{ url_for('admin.settings') }}">
        <div class="form-group">
            <label for="telegram_token">Telegram Bot Token:</label>
            <input type="password" id="telegram_token" name="telegram_token" 
                   value="{{ telegram_token or '' }}" 
                   placeholder="Введите токен Telegram бота">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Токен можно получить у @BotFather в Telegram
            </small>
        </div>
        <button type="submit" class="btn btn-primary">Сохранить настройки</button>
    </form>
    
    <div style="margin-top: 30px; padding: 15px; background: #f8f9fa; border-radius: 5px;">
        <h3>Управление ботом</h3>
        <div style="margin-bottom: 15px;">
            <p><strong>Статус процесса:</strong> 
                <span id="bot-status" style="color: #7f8c8d;">Проверка...</span>
            </p>
            <p id="bot-info" style="margin-top: 10px; color: #7f8c8d; display: none;"></p>
        </div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button type="button" class="btn btn-primary" onclick="checkBotConnection()">
                Проверить подключение
            </button>
            <button type="button" class="btn btn-primary" onclick="restartBot()" id="restart-btn">
                Перезапустить бота
            </button>
        </div>
        <div id="connection-result" style="margin-top: 15px;"></div>
        <div style="margin-top: 20px; padding: 10px; background: #fff3cd; border-radius: 5px; border-left: 4px solid #ffc107;">
            <p style="margin: 0; color: #856404;"><strong>💡 Инструкция по запуску бота:</strong></p>
            <p style="margin-top: 5px; color: #856404; font-size: 13px;">
                Для запуска бота откройте новый терминал и выполните:
            </p>
            <code style="display: block; margin-top: 5px; padding: 8px; background: white; border-radius: 3px; font-family: monospace;">
                cd путь_к_проекту<br>
                python run_bot.py
            </code>
            <p style="margin-top: 10px; margin-bottom: 0; color: #856404; font-size: 12px;">
                ⚠️ Кнопка "Перезапустить бота" может не работать на Windows. Используйте ручной запуск через терминал.
            </p>
        </div>
    </div>
</div>

<script>
function updateBotStatus() {
    fetch('{{ url_for("admin.bot_status") }}')
        .then(response => response.json())
        .then(data => {
            const statusEl = document.getElementById('bot-status');
            const infoEl = document.getElementById('bot-info');
            if (data.running) {
                statusEl.textContent = 'Запущен (PID: ' + data.pid + ')';
                statusEl.style.color = '#27ae60';
                infoEl.style.display = 'block';
                infoEl.textContent = 'Процесс бота активен';
            } else {
                statusEl.textContent = 'Остановлен';
                statusEl.style.color = '#e74c3c';
                infoEl.style.display = 'none';
            }
        })
        .catch(error => {
            document.getElementById('bot-status').textContent = 'Ошибка проверки';
            document.getElementById('bot-status').style.color = '#e74c3c';
        });
}

async function checkBotConnection() {
    const resultEl = document.getElementById('connection-result');
    resultEl.innerHTML = '<div class="alert alert-info">Проверка подключения...</div>';
    
    try {
        const response = await fetch('{{ url_for("admin.check_connection") }}');
        const data = await response.json();
        
        if (data.success) {
            resultEl.innerHTML = '<div class="alert alert-success">' +
                '<strong>Подключение успешно!</strong><br>' +
                'ID: ' + data.bot_id + '<br>' +
                'Username: @' + data.bot_username + '<br>' +
                'Имя: ' + data.bot_first_name +
                '</div>';
        } else {
            resultEl.innerHTML = '<div class="alert alert-info">' +
                '<strong>Ошибка подключения:</strong><br>' +
                data.error +
                '</div>';
        }
    } catch (error) {
        resultEl.innerHTML = '<div class="alert alert-info">Ошибка при проверке: ' + error + '</div>';
    }
}

async function restartBot() {
    const btn = document.getElementById('restart-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Перезапуск...';
    
    const resultEl = document.getElementById('connection-result');
    resultEl.innerHTML = '<div class="alert alert-info">Перезапуск бота...</div>';
    
    try {
        const response = await fetch('{{ url_for("admin.restart_bot_endpoint") }}', {method: 'POST'});
        const data = await response.json();
        
        if (data.success) {
            resultEl.innerHTML = '<div class="alert alert-success">Бот успешно перезапущен!</div>';
            setTimeout(updateBotStatus, 2000);
        } else {
            resultEl.innerHTML = '<div class="alert alert-info">Ошибка: ' + (data.error || 'Неизвестная ошибка') + '</div>';
        }
    } catch (error) {
        resultEl.innerHTML = '<div class="alert alert-info">Ошибка при перезапуске: ' + error + '</div>';
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Обновляем статус при загрузке страницы
updateBotStatus();
setInterval(updateBotStatus, 10000); // Обновляем каждые 10 секунд
</script>
{% endblock %}
''')

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """Страница настроек"""
    logger = logging.getLogger(__name__)
    
    if request.method == 'POST':
        telegram_token = request.form.get('telegram_token', '').strip()
        
        if telegram_token:
            # Сохраняем токен в базу данных
            db.set_system_setting('telegram_bot_token', telegram_token)
            # Также обновляем .env файл если возможно
            try:
                import os
                env_path = '.env'
                if os.path.exists(env_path):
                    with open(env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    updated = False
                    with open(env_path, 'w', encoding='utf-8') as f:
                        for line in lines:
                            if line.startswith('TELEGRAM_BOT_TOKEN='):
                                f.write(f'TELEGRAM_BOT_TOKEN={telegram_token}\n')
                                updated = True
                            else:
                                f.write(line)
                        
                        if not updated:
                            f.write(f'\nTELEGRAM_BOT_TOKEN={telegram_token}\n')
            except Exception as e:
                logger.warning(f"Не удалось обновить .env файл: {e}")
            
            return render_template_string(
                SETTINGS_TEMPLATE, 
                telegram_token=telegram_token,
                message='Настройки успешно сохранены!',
                message_type='success',
                active_page='settings'
            )
        else:
            return render_template_string(
                SETTINGS_TEMPLATE,
                telegram_token=db.get_system_setting('telegram_bot_token'),
                message='Токен не может быть пустым',
                message_type='info',
                active_page='settings'
            )
    
    # GET запрос - показываем форму
    telegram_token = db.get_system_setting('telegram_bot_token')
    # Если в БД нет, пробуем получить из .env
    if not telegram_token:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    return render_template_string(
        SETTINGS_TEMPLATE,
        telegram_token=telegram_token,
        active_page='settings'
    )

@admin_bp.route('/user/<int:user_id>')
@login_required
def user_details(user_id):
    """Детальная информация о пользователе"""
    user = db.get_user_details(user_id)
    if not user:
        return "Пользователь не найден", 404
    
    calendars = db.get_user_calendars(user_id)
    settings = db.get_notification_settings(user_id)
    
    template = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="section">
    <h2>Пользователь #{{ user.user_id }}</h2>
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <p><strong>Имя:</strong> {{ user.first_name or 'N/A' }}</p>
        <p><strong>Username:</strong> @{{ user.username or 'N/A' }}</p>
        <p><strong>Календарей:</strong> {{ user.calendar_count }}</p>
        <p><strong>Уведомлений:</strong> {{ user.notification_count }}</p>
        <p><strong>Дата регистрации:</strong> {{ user.created_at }}</p>
    </div>
    <h3>Календари</h3>
    <table>
        <tr><th>Тип</th><th>Название</th></tr>
        {% for cal in calendars %}
        <tr>
            <td>{{ cal.calendar_type }}</td>
            <td>{{ cal.calendar_name or 'N/A' }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
''')
    from flask import render_template_string
    return render_template_string(template, user=user, calendars=calendars, settings=settings, active_page='users')

@admin_bp.route('/api/bot/status')
@login_required
def bot_status():
    """API для получения статуса бота"""
    running = is_bot_running()
    pid = get_bot_pid()
    return jsonify({
        'running': running,
        'pid': pid
    })

@admin_bp.route('/api/bot/check-connection')
@login_required
def check_connection():
    """API для проверки подключения к боту"""
    try:
        # Используем новый event loop в отдельном потоке
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, check_bot_connection())
            result = future.result(timeout=10)
        
        return jsonify(result)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при проверке подключения: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@admin_bp.route('/api/bot/restart', methods=['POST'])
@login_required
def restart_bot_endpoint():
    """API для перезапуска бота"""
    try:
        success = restart_bot()
        if success:
            return jsonify({
                'success': True,
                'message': 'Бот успешно перезапущен'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Не удалось перезапустить бота'
            })
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при перезапуске бота: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

