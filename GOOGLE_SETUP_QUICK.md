# Быстрая настройка Google OAuth

## Проблема
Ошибка "OAuth client was not found" означает, что Google OAuth приложение не настроено.

## Решение

### 1. Создайте OAuth приложение в Google Cloud Console

1. Откройте: https://console.cloud.google.com/
2. Создайте проект (или выберите существующий)
3. Перейдите: APIs & Services → Credentials
4. Нажмите: Create Credentials → OAuth client ID
5. Если нужно, настройте OAuth consent screen (выберите External, заполните минимальные данные)
6. Создайте OAuth client:
   - Type: Web application
   - Name: Calendar Bot
   - Authorized redirect URIs: `http://localhost:5000/callback/google`
7. Скопируйте Client ID и Client secret

### 2. Обновите .env файл

Откройте `.env` и замените:
```
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback/google
```

На реальные значения:
```
GOOGLE_CLIENT_ID=ваш_реальный_client_id
GOOGLE_CLIENT_SECRET=ваш_реальный_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback/google
```

### 3. Важно!

- Redirect URI в Google Console ДОЛЖЕН точно совпадать с тем, что в .env
- Используйте `http://localhost:5000` (не 8080!)
- После изменения .env перезапустите Flask сервер

### 4. Проверка

После настройки попробуйте снова подключить Google Calendar через бота.

