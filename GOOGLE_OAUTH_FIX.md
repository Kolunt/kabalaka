# Решение проблемы "OAuth client was not found" (401: invalid_client)

## Проблема
Ошибка "The OAuth client was not found" означает, что Google не может найти OAuth приложение с указанным Client ID.

## Проверка текущей конфигурации

Ваши credentials:
- Client ID: `730550260978-jlk79esc3lau4q4m7fnhndeiuc9hcngi.apps.googleusercontent.com` ✅ (правильный формат)
- Client Secret: `GOCSPX-...` ✅ (правильный формат)
- Redirect URI: `http://localhost:5000/callback/google` ✅ (исправлено)

## Возможные причины и решения

### 1. Client ID не существует в Google Cloud Console

**Решение:**
1. Откройте: https://console.cloud.google.com/
2. Убедитесь, что вы выбрали **правильный проект**
3. Перейдите: **APIs & Services** → **Credentials**
4. Найдите OAuth 2.0 Client ID, который начинается с `730550260978-...`
5. Если его нет - нужно создать новое OAuth приложение

### 2. Client ID из другого проекта

**Решение:**
1. Проверьте, в каком проекте создан Client ID
2. Убедитесь, что вы используете credentials из того же проекта
3. Или создайте новое OAuth приложение в текущем проекте

### 3. OAuth приложение было удалено или деактивировано

**Решение:**
Создайте новое OAuth приложение:
1. В Google Cloud Console: **APIs & Services** → **Credentials**
2. Нажмите: **Create Credentials** → **OAuth client ID**
3. Если нужно, настройте OAuth consent screen:
   - Application type: **External**
   - App name: Calendar Bot
   - User support email: ваш email
   - Developer contact: ваш email
   - Scopes: добавьте `https://www.googleapis.com/auth/calendar.readonly`
   - Test users: добавьте `kolunt@gmail.com`
4. Создайте OAuth client:
   - Application type: **Web application**
   - Name: Calendar Bot
   - Authorized redirect URIs: `http://localhost:5000/callback/google`
5. Скопируйте **новые** Client ID и Client Secret
6. Обновите `.env` файл с новыми значениями

### 4. Проверка в Google Cloud Console

Убедитесь, что:
- ✅ OAuth 2.0 Client ID существует и активен
- ✅ Client ID точно совпадает с тем, что в `.env`
- ✅ Client Secret точно совпадает с тем, что в `.env`
- ✅ В "Authorized redirect URIs" указан: `http://localhost:5000/callback/google`
- ✅ Google Calendar API включен в проекте

### 5. Проверка на лишние пробелы

В `.env` файле убедитесь, что нет лишних пробелов:
```
GOOGLE_CLIENT_ID=730550260978-jlk79esc3lau4q4m7fnhndeiuc9hcngi.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-ваш_секрет_без_пробелов
GOOGLE_REDIRECT_URI=http://localhost:5000/callback/google
```

## Рекомендуемое решение

**Создайте новое OAuth приложение:**

1. В Google Cloud Console создайте новый OAuth 2.0 Client ID
2. Скопируйте новые Client ID и Client Secret
3. Обновите `.env` файл
4. Убедитесь, что redirect URI указан правильно в обоих местах
5. Перезапустите Flask сервер

## После исправления

1. Перезапустите Flask сервер
2. Попробуйте снова подключить Google Calendar
3. Ошибка должна исчезнуть




