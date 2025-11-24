# Инструкция по развертыванию на PythonAnywhere

## Шаг 1: Загрузка файлов

1. Загрузите все файлы проекта на PythonAnywhere через Files tab
2. Убедитесь, что все файлы находятся в одной директории

## Шаг 2: Установка зависимостей

1. Откройте Bash консоль на PythonAnywhere
2. Перейдите в директорию проекта:
   ```bash
   cd ~/alarm-bot
   ```
3. Установите зависимости:
   ```bash
   pip3.10 install --user -r requirements.txt
   ```

## Шаг 3: Настройка переменных окружения

1. Создайте файл `.env` в корне проекта
2. Заполните все необходимые переменные (см. `.env.example`)

## Шаг 4: Инициализация базы данных

В Bash консоли выполните:
```bash
python3.10 init_db.py
```

## Шаг 5: Создание администратора

В Bash консоли выполните:
```bash
python3.10 create_admin.py
```

Введите имя пользователя и пароль для администратора. Это будет единственный администратор системы.

## Шаг 6: Настройка Web App

1. Перейдите в раздел Web
2. Создайте новый Web app или используйте существующий
3. В разделе "Code" укажите:
   - Source code: `/home/yourusername/alarm-bot`
   - WSGI configuration file: выберите файл или создайте новый

4. Отредактируйте WSGI файл (например, `/var/www/yourusername_pythonanywhere_com_wsgi.py`):
   ```python
   import sys
   import os

   # Добавьте путь к проекту
   path = '/home/yourusername/alarm-bot'
   if path not in sys.path:
       sys.path.insert(0, path)

   # Импортируйте приложение
   from app import app as application

   if __name__ == "__main__":
       application.run()
   ```

5. В разделе "Static files" добавьте (если нужно):
   - URL: `/static`
   - Directory: `/home/yourusername/alarm-bot/static`

## Шаг 7: Настройка Scheduled Tasks

1. Перейдите в раздел Tasks
2. Создайте новую задачу:
   - Command: `cd /home/yourusername/alarm-bot && python3.10 -c "import asyncio; from scheduler import check_and_notify_events; asyncio.run(check_and_notify_events())"`
   - Hour: `*` (каждый час)
   - Minute: `*/5` (каждые 5 минут) или другое значение из `CHECK_INTERVAL_MINUTES`

## Шаг 8: Настройка OAuth Redirect URIs

### Google Calendar
1. В Google Cloud Console добавьте redirect URI:
   `https://yourusername.pythonanywhere.com/callback/google`

### Yandex Calendar
1. В настройках приложения Yandex добавьте redirect URI:
   `https://yourusername.pythonanywhere.com/callback/yandex`

## Шаг 9: Обновление конфигурации

В файле `.env` обновите redirect URIs:
```
GOOGLE_REDIRECT_URI=https://yourusername.pythonanywhere.com/callback/google
YANDEX_REDIRECT_URI=https://yourusername.pythonanywhere.com/callback/yandex
```

## Шаг 10: Запуск бота

### Вариант 1: Через Web App (рекомендуется)
1. Web app будет автоматически запускаться при старте сервера
2. Проверьте логи в разделе Web -> Error log

### Вариант 2: Через Always-on task (для polling)
1. Перейдите в раздел Tasks
2. Создайте Always-on task:
   - Command: `cd /home/yourusername/alarm-bot && python3.10 main.py`
   - Это запустит бота в режиме polling

## Проверка работы

1. Откройте в браузере: `https://yourusername.pythonanywhere.com/`
2. Должно произойти перенаправление на `/admin/login`
3. Войдите в админ панель используя созданные учетные данные
4. Проверьте health endpoint: `https://yourusername.pythonanywhere.com/health`

### Админ панель

- URL: `https://yourusername.pythonanywhere.com/admin/login`
- Доступна только для созданного администратора
- В админ панели доступна статистика, список пользователей и их календари

## Важные замечания

- На бесплатном тарифе PythonAnywhere приложение может "засыпать" после неактивности
- Используйте Always-on task для постоянной работы бота
- Scheduled tasks выполняются только если Web app активен
- Логи можно просматривать в разделе Web -> Error log

## Решение проблем

### Бот не отвечает
- Проверьте, что Always-on task запущен
- Проверьте логи в Error log
- Убедитесь, что токен бота правильный

### OAuth не работает
- Проверьте redirect URIs в настройках OAuth приложений
- Убедитесь, что Web app доступен по HTTPS
- Проверьте логи для деталей ошибок

### События не проверяются
- Убедитесь, что Scheduled task настроен правильно
- Проверьте, что Web app активен
- Проверьте логи в Error log

