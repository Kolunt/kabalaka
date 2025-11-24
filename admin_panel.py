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
        .settings-layout {
            display: flex;
            gap: 20px;
            margin-top: 20px;
        }
        .settings-sidebar {
            width: 250px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px 0;
            height: fit-content;
        }
        .settings-sidebar a {
            display: block;
            padding: 12px 20px;
            color: #2c3e50;
            text-decoration: none;
            transition: background 0.3s;
            border-left: 3px solid transparent;
        }
        .settings-sidebar a:hover {
            background: #f8f9fa;
        }
        .settings-sidebar a.active {
            background: #e8f4f8;
            border-left-color: #3498db;
            color: #3498db;
            font-weight: bold;
        }
        .settings-content {
            flex: 1;
        }
        .form-group input[type="number"],
        .form-group input[type="checkbox"] {
            width: auto;
            margin-right: 8px;
        }
        .form-group input[type="number"] {
            width: 100px;
        }
        .badge-secondary {
            background: #95a5a6;
            color: white;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <h1>Админ панель - Kabalaka</h1>
            <a href="{{ url_for('admin.logout') }}" class="logout">Выйти</a>
        </div>
    </div>
    <div class="nav">
        <div class="nav-content">
            <a href="{{ url_for('admin.dashboard') }}" class="{% if active_page == 'dashboard' %}active{% endif %}">Дашборд</a>
            <a href="{{ url_for('admin.users') }}" class="{% if active_page == 'users' %}active{% endif %}">Пользователи</a>
            <a href="{{ url_for('admin.broadcasts') }}" class="{% if active_page == 'broadcasts' %}active{% endif %}">Рассылки</a>
            <a href="{{ url_for('admin.settings_general') }}" class="{% if active_page == 'settings' %}active{% endif %}">Настройки</a>
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
            <th>Язык</th>
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
            <td>
                {% if user.language %}
                    <span class="badge badge-secondary">{{ language_names.get(user.language, user.language.upper()) }}</span>
                {% else %}
                    <span class="badge badge-secondary">EN (default)</span>
                {% endif %}
            </td>
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

# Базовый шаблон для страниц настроек с боковым меню
SETTINGS_BASE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="settings-layout">
    <div class="settings-sidebar">
        <a href="{{ url_for("admin.settings_general") }}" class="{% if settings_subpage == 'general' %}active{% endif %}">
            ⚙️ Основные настройки
        </a>
        <a href="{{ url_for("admin.settings_scheduler") }}" class="{% if settings_subpage == 'scheduler' %}active{% endif %}">
            ⏰ Планировщик
        </a>
        <a href="{{ url_for("admin.settings_bot") }}" class="{% if settings_subpage == 'bot' %}active{% endif %}">
            🤖 Управление ботом
        </a>
    </div>
    <div class="settings-content">
        {% block settings_content %}{% endblock %}
    </div>
</div>
{% endblock %}
''')

# Шаблон основных настроек
SETTINGS_GENERAL_TEMPLATE = SETTINGS_BASE_TEMPLATE.replace('{% block settings_content %}{% endblock %}', '''
{% block settings_content %}
<div class="section">
    <h2>Основные настройки</h2>
    {% if message %}
    <div class="alert alert-{{ message_type or 'success' }}">{{ message }}</div>
    {% endif %}
    <form method="POST" action="{{ url_for('admin.settings_general') }}">
        <h3 style="margin-bottom: 15px; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">Telegram</h3>
        <div class="form-group">
            <label for="telegram_token">Telegram Bot Token:</label>
            <input type="password" id="telegram_token" name="telegram_token" 
                   value="{{ telegram_token or '' }}" 
                   placeholder="Введите токен Telegram бота">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Токен можно получить у @BotFather в Telegram
            </small>
        </div>
        
        <h3 style="margin-top: 30px; margin-bottom: 15px; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">Google Calendar</h3>
        <div class="form-group">
            <label for="google_client_id">Google Client ID:</label>
            <input type="text" id="google_client_id" name="google_client_id" 
                   value="{{ google_client_id or '' }}" 
                   placeholder="Введите Google Client ID">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Получить можно в Google Cloud Console
            </small>
        </div>
        <div class="form-group">
            <label for="google_client_secret">Google Client Secret:</label>
            <input type="password" id="google_client_secret" name="google_client_secret" 
                   value="{{ google_client_secret or '' }}" 
                   placeholder="Введите Google Client Secret">
        </div>
        <div class="form-group">
            <label for="google_redirect_uri">Google Redirect URI:</label>
            <input type="text" id="google_redirect_uri" name="google_redirect_uri" 
                   value="{{ google_redirect_uri or '' }}" 
                   placeholder="http://localhost:5000/callback/google">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Должен совпадать с настройками в Google Cloud Console
            </small>
        </div>
        
        <h3 style="margin-top: 30px; margin-bottom: 15px; color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px;">Yandex Calendar</h3>
        <div class="form-group">
            <label for="yandex_client_id">Yandex Client ID:</label>
            <input type="text" id="yandex_client_id" name="yandex_client_id" 
                   value="{{ yandex_client_id or '' }}" 
                   placeholder="Введите Yandex Client ID">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Получить можно в Yandex OAuth
            </small>
        </div>
        <div class="form-group">
            <label for="yandex_client_secret">Yandex Client Secret:</label>
            <input type="password" id="yandex_client_secret" name="yandex_client_secret" 
                   value="{{ yandex_client_secret or '' }}" 
                   placeholder="Введите Yandex Client Secret">
        </div>
        <div class="form-group">
            <label for="yandex_redirect_uri">Yandex Redirect URI:</label>
            <input type="text" id="yandex_redirect_uri" name="yandex_redirect_uri" 
                   value="{{ yandex_redirect_uri or '' }}" 
                   placeholder="http://localhost:5000/callback/yandex">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Должен совпадать с настройками в Yandex OAuth
            </small>
        </div>
        
        <button type="submit" class="btn btn-primary">Сохранить настройки</button>
    </form>
</div>
{% endblock %}
''')

# Шаблон настроек планировщика
SETTINGS_SCHEDULER_TEMPLATE = SETTINGS_BASE_TEMPLATE.replace('{% block settings_content %}{% endblock %}', '''
{% block settings_content %}
<div class="section">
    <h2>Настройки планировщика</h2>
    {% if message %}
    <div class="alert alert-{{ message_type or 'success' }}">{{ message }}</div>
    {% endif %}
    <form method="POST" action="{{ url_for('admin.settings_scheduler') }}">
        <div class="form-group">
            <label for="check_interval">Интервал проверки событий (минуты):</label>
            <input type="number" id="check_interval" name="check_interval" 
                   value="{{ check_interval or 5 }}" 
                   min="1" max="60" step="1"
                   placeholder="Интервал в минутах">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Как часто планировщик будет проверять события календарей (рекомендуется: 5 минут)
            </small>
        </div>
        <div class="form-group">
            <label>
                <input type="checkbox" id="scheduler_enabled" name="scheduler_enabled" 
                       {% if scheduler_enabled %}checked{% endif %}>
                Включить планировщик
            </label>
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Если выключено, проверка событий не будет выполняться автоматически
            </small>
        </div>
        <button type="submit" class="btn btn-primary">Сохранить настройки</button>
    </form>
</div>
{% endblock %}
''')

# Шаблон управления ботом
SETTINGS_BOT_TEMPLATE = SETTINGS_BASE_TEMPLATE.replace('{% block settings_content %}{% endblock %}', '''
{% block settings_content %}
<div class="section">
    <h2>Управление ботом</h2>
    <div style="margin-bottom: 20px;">
        <p><strong>Статус процесса:</strong> 
            <span id="bot-status" style="color: #7f8c8d;">Проверка...</span>
        </p>
        <p id="bot-info" style="margin-top: 10px; color: #7f8c8d; display: none;"></p>
        <p style="margin-top: 10px;"><strong>Статус подключения к TG-боту:</strong> 
            <span id="tg-connection-status" style="color: #7f8c8d;">Проверка...</span>
        </p>
        <p id="tg-connection-info" style="margin-top: 5px; color: #7f8c8d; font-size: 13px; display: none;"></p>
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

function updateTgConnectionStatus() {
    fetch('{{ url_for("admin.check_connection") }}')
        .then(response => response.json())
        .then(data => {
            const statusEl = document.getElementById('tg-connection-status');
            const infoEl = document.getElementById('tg-connection-info');
            if (data.success) {
                statusEl.textContent = 'Подключен';
                statusEl.style.color = '#27ae60';
                infoEl.style.display = 'block';
                infoEl.textContent = '@' + data.bot_username + ' (' + data.bot_first_name + ', ID: ' + data.bot_id + ')';
            } else {
                statusEl.textContent = 'Не подключен';
                statusEl.style.color = '#e74c3c';
                infoEl.style.display = 'block';
                infoEl.textContent = data.error || 'Ошибка подключения';
                infoEl.style.color = '#e74c3c';
            }
        })
        .catch(error => {
            document.getElementById('tg-connection-status').textContent = 'Ошибка проверки';
            document.getElementById('tg-connection-status').style.color = '#e74c3c';
        });
}

// Обновляем статус при загрузке страницы
updateBotStatus();
updateTgConnectionStatus();
setInterval(updateBotStatus, 10000); // Обновляем каждые 10 секунд
setInterval(updateTgConnectionStatus, 15000); // Обновляем статус подключения каждые 15 секунд
</script>
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
    from i18n import SUPPORTED_LANGUAGES
    users_list = db.get_all_users()
    language_names = SUPPORTED_LANGUAGES
    return render_template_string(USERS_TEMPLATE, users=users_list, language_names=language_names, active_page='users')


# Редирект со старого маршрута на новый
@admin_bp.route('/settings')
@login_required
def settings():
    """Редирект на основные настройки"""
    return redirect(url_for('admin.settings_general'))

@admin_bp.route('/settings/general', methods=['GET', 'POST'])
@login_required
def settings_general():
    """Основные настройки"""
    logger = logging.getLogger(__name__)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    # Функция для получения значения из БД или .env
    def get_setting(key, default=''):
        value = db.get_system_setting(key)
        if value:
            return value
        return os.getenv(key, default)
    
    # Функция для обновления .env файла
    def update_env_file(updates):
        """Обновляет .env файл с переданными значениями"""
        try:
            env_path = '.env'
            env_vars = {}
            
            # Читаем существующие значения
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and '=' in line and not line.startswith('#'):
                            key, value = line.split('=', 1)
                            env_vars[key] = value
            
            # Обновляем значения
            env_vars.update(updates)
            
            # Записываем обратно
            with open(env_path, 'w', encoding='utf-8') as f:
                for key, value in env_vars.items():
                    f.write(f'{key}={value}\n')
        except Exception as e:
            logger.warning(f"Не удалось обновить .env файл: {e}")
    
    if request.method == 'POST':
        # Получаем все значения из формы
        telegram_token = request.form.get('telegram_token', '').strip()
        google_client_id = request.form.get('google_client_id', '').strip()
        google_client_secret = request.form.get('google_client_secret', '').strip()
        google_redirect_uri = request.form.get('google_redirect_uri', '').strip()
        yandex_client_id = request.form.get('yandex_client_id', '').strip()
        yandex_client_secret = request.form.get('yandex_client_secret', '').strip()
        yandex_redirect_uri = request.form.get('yandex_redirect_uri', '').strip()
        
        # Валидация обязательных полей
        if not telegram_token:
            # Получаем текущие значения для отображения
            return render_template_string(
                SETTINGS_GENERAL_TEMPLATE,
                telegram_token=get_setting('telegram_bot_token'),
                google_client_id=get_setting('google_client_id'),
                google_client_secret=get_setting('google_client_secret'),
                google_redirect_uri=get_setting('google_redirect_uri', 'http://localhost:5000/callback/google'),
                yandex_client_id=get_setting('yandex_client_id'),
                yandex_client_secret=get_setting('yandex_client_secret'),
                yandex_redirect_uri=get_setting('yandex_redirect_uri', 'http://localhost:5000/callback/yandex'),
                message='Telegram Bot Token не может быть пустым',
                message_type='info',
                active_page='settings',
                settings_subpage='general'
            )
        
        # Сохраняем все настройки в базу данных
        db.set_system_setting('telegram_bot_token', telegram_token)
        if google_client_id:
            db.set_system_setting('google_client_id', google_client_id)
        if google_client_secret:
            db.set_system_setting('google_client_secret', google_client_secret)
        if google_redirect_uri:
            db.set_system_setting('google_redirect_uri', google_redirect_uri)
        if yandex_client_id:
            db.set_system_setting('yandex_client_id', yandex_client_id)
        if yandex_client_secret:
            db.set_system_setting('yandex_client_secret', yandex_client_secret)
        if yandex_redirect_uri:
            db.set_system_setting('yandex_redirect_uri', yandex_redirect_uri)
        
        # Обновляем .env файл
        env_updates = {
            'TELEGRAM_BOT_TOKEN': telegram_token
        }
        if google_client_id:
            env_updates['GOOGLE_CLIENT_ID'] = google_client_id
        if google_client_secret:
            env_updates['GOOGLE_CLIENT_SECRET'] = google_client_secret
        if google_redirect_uri:
            env_updates['GOOGLE_REDIRECT_URI'] = google_redirect_uri
        if yandex_client_id:
            env_updates['YANDEX_CLIENT_ID'] = yandex_client_id
        if yandex_client_secret:
            env_updates['YANDEX_CLIENT_SECRET'] = yandex_client_secret
        if yandex_redirect_uri:
            env_updates['YANDEX_REDIRECT_URI'] = yandex_redirect_uri
        
        update_env_file(env_updates)
        
        return render_template_string(
            SETTINGS_GENERAL_TEMPLATE,
            telegram_token=telegram_token,
            google_client_id=google_client_id,
            google_client_secret=google_client_secret,
            google_redirect_uri=google_redirect_uri or 'http://localhost:5000/callback/google',
            yandex_client_id=yandex_client_id,
            yandex_client_secret=yandex_client_secret,
            yandex_redirect_uri=yandex_redirect_uri or 'http://localhost:5000/callback/yandex',
            message='Настройки успешно сохранены!',
            message_type='success',
            active_page='settings',
            settings_subpage='general'
        )
    
    # GET запрос - показываем форму с текущими значениями
    return render_template_string(
        SETTINGS_GENERAL_TEMPLATE,
        telegram_token=get_setting('telegram_bot_token'),
        google_client_id=get_setting('google_client_id'),
        google_client_secret=get_setting('google_client_secret'),
        google_redirect_uri=get_setting('google_redirect_uri', 'http://localhost:5000/callback/google'),
        yandex_client_id=get_setting('yandex_client_id'),
        yandex_client_secret=get_setting('yandex_client_secret'),
        yandex_redirect_uri=get_setting('yandex_redirect_uri', 'http://localhost:5000/callback/yandex'),
        active_page='settings',
        settings_subpage='general'
    )

@admin_bp.route('/settings/scheduler', methods=['GET', 'POST'])
@login_required
def settings_scheduler():
    """Настройки планировщика"""
    logger = logging.getLogger(__name__)
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    if request.method == 'POST':
        check_interval = request.form.get('check_interval', '5').strip()
        scheduler_enabled = request.form.get('scheduler_enabled') == 'on'
        
        # Валидация
        try:
            check_interval_int = int(check_interval)
            if check_interval_int < 1 or check_interval_int > 60:
                raise ValueError("Интервал должен быть от 1 до 60 минут")
        except ValueError as e:
            # Получаем текущие значения для отображения
            current_interval = db.get_system_setting('check_interval_minutes') or os.getenv('CHECK_INTERVAL_MINUTES', '5')
            enabled_str = db.get_system_setting('scheduler_enabled')
            current_enabled = enabled_str != 'false' if enabled_str else True
            
            return render_template_string(
                SETTINGS_SCHEDULER_TEMPLATE,
                check_interval=current_interval,
                scheduler_enabled=current_enabled,
                message=f'Ошибка: {str(e)}',
                message_type='info',
                active_page='settings',
                settings_subpage='scheduler'
            )
        
        # Сохраняем настройки в базу данных
        db.set_system_setting('check_interval_minutes', str(check_interval_int))
        db.set_system_setting('scheduler_enabled', 'true' if scheduler_enabled else 'false')
        
        # Обновляем планировщик
        try:
            from app import scheduler
            if scheduler:
                # Удаляем старую задачу
                try:
                    scheduler.remove_job('check_events')
                except:
                    pass
                
                # Добавляем новую задачу, если планировщик включен
                if scheduler_enabled:
                    from apscheduler.triggers.interval import IntervalTrigger
                    import asyncio
                    from scheduler import check_and_notify_events
                    
                    scheduler.add_job(
                        func=lambda: asyncio.run(check_and_notify_events()),
                        trigger=IntervalTrigger(minutes=check_interval_int),
                        id='check_events',
                        name='Проверка событий календарей',
                        replace_existing=True
                    )
                    logger.info(f"Планировщик обновлен: интервал {check_interval_int} минут, статус: {'включен' if scheduler_enabled else 'выключен'}")
        except Exception as e:
            logger.warning(f"Не удалось обновить планировщик: {e}")
        
        # Также обновляем .env файл если возможно
        try:
            env_path = '.env'
            if os.path.exists(env_path):
                with open(env_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                updated_interval = False
                with open(env_path, 'w', encoding='utf-8') as f:
                    for line in lines:
                        if line.startswith('CHECK_INTERVAL_MINUTES='):
                            f.write(f'CHECK_INTERVAL_MINUTES={check_interval_int}\n')
                            updated_interval = True
                        else:
                            f.write(line)
                    
                    if not updated_interval:
                        f.write(f'\nCHECK_INTERVAL_MINUTES={check_interval_int}\n')
        except Exception as e:
            logger.warning(f"Не удалось обновить .env файл: {e}")
        
        return render_template_string(
            SETTINGS_SCHEDULER_TEMPLATE,
            check_interval=check_interval_int,
            scheduler_enabled=scheduler_enabled,
            message='Настройки успешно сохранены!',
            message_type='success',
            active_page='settings',
            settings_subpage='scheduler'
        )
    
    # GET запрос - показываем форму
    check_interval = db.get_system_setting('check_interval_minutes')
    if not check_interval:
        check_interval = os.getenv('CHECK_INTERVAL_MINUTES', '5')
    
    scheduler_enabled_str = db.get_system_setting('scheduler_enabled')
    scheduler_enabled = scheduler_enabled_str != 'false' if scheduler_enabled_str else True
    
    return render_template_string(
        SETTINGS_SCHEDULER_TEMPLATE,
        check_interval=check_interval,
        scheduler_enabled=scheduler_enabled,
        active_page='settings',
        settings_subpage='scheduler'
    )

@admin_bp.route('/settings/bot')
@login_required
def settings_bot():
    """Управление ботом"""
    return render_template_string(
        SETTINGS_BOT_TEMPLATE,
        active_page='settings',
        settings_subpage='bot'
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
        <p><strong>Язык:</strong> 
            {% if user.language %}
                <span class="badge badge-secondary">{{ language_names.get(user.language, user.language.upper()) }}</span>
            {% else %}
                <span class="badge badge-secondary">English (default)</span>
            {% endif %}
        </p>
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
    from i18n import SUPPORTED_LANGUAGES
    return render_template_string(template, user=user, calendars=calendars, settings=settings, language_names=SUPPORTED_LANGUAGES, active_page='users')

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

# Шаблоны для рассылок
BROADCASTS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="section">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2>Рассылки</h2>
        <a href="{{ url_for('admin.broadcast_create') }}" class="btn btn-primary">+ Создать рассылку</a>
    </div>
    {% if message %}
    <div class="alert alert-{{ message_type or 'success' }}">{{ message }}</div>
    {% endif %}
    <table>
        <tr>
            <th>ID</th>
            <th>Сообщение</th>
            <th>Языки</th>
            <th>Статус</th>
            <th>Отправлено</th>
            <th>Ошибок</th>
            <th>Создано</th>
            <th>Действия</th>
        </tr>
        {% for broadcast in broadcasts %}
        <tr>
            <td>{{ broadcast.id }}</td>
            <td style="max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                {{ broadcast.message_text[:50] }}{% if broadcast.message_text|length > 50 %}...{% endif %}
            </td>
            <td>
                {% if broadcast.languages %}
                    {% for lang in broadcast.languages %}
                        <span class="badge badge-secondary">{{ language_names.get(lang, lang.upper()) }}</span>
                    {% endfor %}
                {% else %}
                    <span class="badge badge-info">Все</span>
                {% endif %}
            </td>
            <td>
                {% if broadcast.status == 'pending' %}
                    <span class="badge badge-info">Ожидает</span>
                {% elif broadcast.status == 'sending' %}
                    <span class="badge badge-info">Отправляется</span>
                {% elif broadcast.status == 'completed' %}
                    <span class="badge badge-success">Завершена</span>
                {% elif broadcast.status == 'failed' %}
                    <span class="badge badge-secondary" style="background: #e74c3c;">Ошибка</span>
                {% endif %}
            </td>
            <td>{{ broadcast.sent_count or 0 }}/{{ broadcast.total_users or 0 }}</td>
            <td>{{ broadcast.failed_count or 0 }}</td>
            <td>{{ broadcast.created_at[:16] if broadcast.created_at else 'N/A' }}</td>
            <td>
                <a href="{{ url_for('admin.broadcast_details', broadcast_id=broadcast.id) }}" class="user-link">Подробнее</a>
            </td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
''')

BROADCAST_CREATE_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="section">
    <h2>Создать рассылку</h2>
    {% if message %}
    <div class="alert alert-{{ message_type or 'success' }}">{{ message }}</div>
    {% endif %}
    <form method="POST" action="{{ url_for('admin.broadcast_create') }}">
        <div class="form-group">
            <label for="message_text">Текст сообщения:</label>
            <textarea id="message_text" name="message_text" rows="6" 
                      style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;"
                      placeholder="Введите текст сообщения для рассылки" required>{{ message_text or '' }}</textarea>
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Сообщение будет отправлено всем пользователям (или выбранным языкам)
            </small>
        </div>
        
        <div class="form-group">
            <label>Выберите языки (оставьте пустым для всех):</label>
            <div style="margin-top: 10px;">
                {% for lang_code, lang_name in language_names.items() %}
                <label style="display: inline-block; margin-right: 15px; margin-bottom: 10px;">
                    <input type="checkbox" name="languages" value="{{ lang_code }}" 
                           {% if selected_languages and lang_code in selected_languages %}checked{% endif %}>
                    {{ lang_name }}
                </label>
                {% endfor %}
            </div>
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Если не выбрано ни одного языка, сообщение будет отправлено всем пользователям
            </small>
        </div>
        
        <div class="form-group">
            <label>
                <input type="checkbox" id="schedule_enabled" name="schedule_enabled" 
                       {% if scheduled_at %}checked{% endif %}
                       onchange="document.getElementById('schedule_datetime').disabled = !this.checked">
                Отложенная отправка
            </label>
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Если включено, сообщение будет отправлено в указанное время
            </small>
        </div>
        
        <div class="form-group">
            <label for="schedule_datetime">Дата и время отправки:</label>
            <input type="datetime-local" id="schedule_datetime" name="schedule_datetime" 
                   value="{{ scheduled_at or '' }}"
                   {% if not scheduled_at %}disabled{% endif %}
                   style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;">
            <small style="color: #7f8c8d; display: block; margin-top: 5px;">
                Укажите дату и время для отложенной отправки (время сервера)
            </small>
        </div>
        
        <div style="display: flex; gap: 10px;">
            <button type="submit" class="btn btn-primary">Создать рассылку</button>
            <a href="{{ url_for('admin.broadcasts') }}" class="btn" style="background: #95a5a6; color: white;">Отмена</a>
        </div>
    </form>
</div>
{% endblock %}
''')

BROADCAST_DETAILS_TEMPLATE = BASE_TEMPLATE.replace('{% block content %}{% endblock %}', '''
{% block content %}
<div class="section">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
        <h2>Рассылка #{{ broadcast.id }}</h2>
        <a href="{{ url_for('admin.broadcasts') }}" class="btn" style="background: #95a5a6; color: white;">← Назад</a>
    </div>
    
    <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <p><strong>Текст сообщения:</strong></p>
        <div style="background: white; padding: 15px; border-radius: 5px; margin-top: 10px; white-space: pre-wrap;">{{ broadcast.message_text }}</div>
        
        <p style="margin-top: 15px;"><strong>Языки:</strong> 
            {% if broadcast.languages %}
                {% for lang in broadcast.languages %}
                    <span class="badge badge-secondary">{{ language_names.get(lang, lang.upper()) }}</span>
                {% endfor %}
            {% else %}
                <span class="badge badge-info">Все языки</span>
            {% endif %}
        </p>
        
        <p><strong>Статус:</strong> 
            {% if broadcast.status == 'pending' %}
                <span class="badge badge-info">Ожидает отправки</span>
            {% elif broadcast.status == 'sending' %}
                <span class="badge badge-info">Отправляется</span>
            {% elif broadcast.status == 'completed' %}
                <span class="badge badge-success">Завершена</span>
            {% elif broadcast.status == 'failed' %}
                <span class="badge badge-secondary" style="background: #e74c3c;">Ошибка</span>
            {% endif %}
        </p>
        
        <p><strong>Создано:</strong> {{ broadcast.created_at or 'N/A' }}</p>
        {% if broadcast.scheduled_at %}
        <p><strong>Запланировано на:</strong> {{ broadcast.scheduled_at }}</p>
        {% endif %}
        {% if broadcast.started_at %}
        <p><strong>Начато:</strong> {{ broadcast.started_at }}</p>
        {% endif %}
        {% if broadcast.completed_at %}
        <p><strong>Завершено:</strong> {{ broadcast.completed_at }}</p>
        {% endif %}
        <p><strong>Статистика:</strong> Отправлено: {{ broadcast.sent_count or 0 }} / Всего: {{ broadcast.total_users or 0 }}, Ошибок: {{ broadcast.failed_count or 0 }}</p>
    </div>
    
    <h3>История отправок</h3>
    <table>
        <tr>
            <th>Пользователь</th>
            <th>Язык</th>
            <th>Статус</th>
            <th>Ошибка</th>
            <th>Время</th>
        </tr>
        {% for item in history %}
        <tr>
            <td>
                {% if item.first_name %}
                    {{ item.first_name }}
                    {% if item.username %}(@{{ item.username }}){% endif %}
                {% else %}
                    ID: {{ item.user_id }}
                {% endif %}
            </td>
            <td>
                <span class="badge badge-secondary">{{ language_names.get(item.language, item.language or 'N/A') }}</span>
            </td>
            <td>
                {% if item.status == 'sent' %}
                    <span class="badge badge-success">Отправлено</span>
                {% elif item.status == 'failed' %}
                    <span class="badge badge-secondary" style="background: #e74c3c;">Ошибка</span>
                {% elif item.status == 'skipped' %}
                    <span class="badge badge-info">Пропущено</span>
                {% endif %}
            </td>
            <td style="color: #e74c3c; font-size: 12px;">{{ item.error_message or '-' }}</td>
            <td>{{ item.sent_at[:19] if item.sent_at else '-' }}</td>
        </tr>
        {% endfor %}
    </table>
</div>
{% endblock %}
''')

@admin_bp.route('/broadcasts')
@login_required
def broadcasts():
    """Страница со списком рассылок"""
    from i18n import SUPPORTED_LANGUAGES
    broadcasts_list = db.get_all_broadcasts()
    language_names = SUPPORTED_LANGUAGES
    return render_template_string(BROADCASTS_TEMPLATE, broadcasts=broadcasts_list, language_names=language_names, active_page='broadcasts')

@admin_bp.route('/broadcasts/create', methods=['GET', 'POST'])
@login_required
def broadcast_create():
    """Создание новой рассылки"""
    from i18n import SUPPORTED_LANGUAGES
    from datetime import datetime
    import json
    
    language_names = SUPPORTED_LANGUAGES
    
    if request.method == 'POST':
        message_text = request.form.get('message_text', '').strip()
        languages = request.form.getlist('languages')
        schedule_enabled = request.form.get('schedule_enabled') == 'on'
        schedule_datetime = request.form.get('schedule_datetime', '').strip()
        
        if not message_text:
            return render_template_string(
                BROADCAST_CREATE_TEMPLATE,
                message='Текст сообщения не может быть пустым',
                message_type='info',
                language_names=language_names,
                active_page='broadcasts'
            )
        
        scheduled_at = None
        if schedule_enabled and schedule_datetime:
            try:
                # Преобразуем datetime-local в datetime
                scheduled_at = datetime.fromisoformat(schedule_datetime.replace('T', ' '))
            except ValueError:
                return render_template_string(
                    BROADCAST_CREATE_TEMPLATE,
                    message='Неверный формат даты и времени',
                    message_type='info',
                    message_text=message_text,
                    selected_languages=languages,
                    language_names=language_names,
                    active_page='broadcasts'
                )
        
        # Создаем рассылку
        created_by = session.get('admin_username', 'admin')
        broadcast_id = db.create_broadcast(
            message_text=message_text,
            languages=languages if languages else None,
            scheduled_at=scheduled_at,
            created_by=created_by
        )
        
        # Если рассылка немедленная, запускаем отправку
        if not scheduled_at:
            # Запускаем отправку в фоне
            try:
                from broadcast_sender import send_broadcast
                import threading
                thread = threading.Thread(target=send_broadcast, args=(broadcast_id,))
                thread.daemon = True
                thread.start()
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка при запуске рассылки: {e}")
        
        return redirect(url_for('admin.broadcast_details', broadcast_id=broadcast_id))
    
    # GET запрос - показываем форму
    return render_template_string(
        BROADCAST_CREATE_TEMPLATE,
        language_names=language_names,
        active_page='broadcasts'
    )

@admin_bp.route('/broadcasts/<int:broadcast_id>')
@login_required
def broadcast_details(broadcast_id):
    """Детальная информация о рассылке"""
    from i18n import SUPPORTED_LANGUAGES
    broadcast = db.get_broadcast(broadcast_id)
    if not broadcast:
        return "Рассылка не найдена", 404
    
    history = db.get_broadcast_history(broadcast_id)
    language_names = SUPPORTED_LANGUAGES
    
    return render_template_string(
        BROADCAST_DETAILS_TEMPLATE,
        broadcast=broadcast,
        history=history,
        language_names=language_names,
        active_page='broadcasts'
    )

