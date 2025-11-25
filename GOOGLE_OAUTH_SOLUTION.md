# Решение проблемы "OAuth client was not found"

## ✅ Хорошие новости

Ваши credentials **правильные** и authorization URL создается успешно. Проблема в настройках Google Cloud Console.

## 🔍 Что проверить в Google Cloud Console

### 1. Проверьте OAuth Consent Screen

1. Откройте: https://console.cloud.google.com/
2. Выберите проект с Client ID `730550260978-...`
3. Перейдите: **APIs & Services** → **OAuth consent screen**
4. Убедитесь, что:
   - **User Type**: External (для тестирования)
   - **App name**: указано (например, "Calendar Bot")
   - **User support email**: ваш email
   - **Developer contact**: ваш email
   - **Scopes**: добавлен `https://www.googleapis.com/auth/calendar.readonly`
   - **Test users**: добавлен `kolunt@gmail.com` ⚠️ **ВАЖНО!**

### 2. Проверьте OAuth 2.0 Client ID

1. Перейдите: **APIs & Services** → **Credentials**
2. Найдите OAuth 2.0 Client ID, который начинается с `730550260978-...`
3. Нажмите на него для редактирования
4. Проверьте:
   - **Application type**: Web application
   - **Name**: Calendar Bot (или другое)
   - **Authorized redirect URIs**: должен быть **точно**:
     ```
     http://localhost:5000/callback/google
     ```
   - ⚠️ Убедитесь, что нет лишних пробелов или символов!

### 3. Проверьте, что Google Calendar API включен

1. Перейдите: **APIs & Services** → **Library**
2. Найдите "Google Calendar API"
3. Убедитесь, что API **Enabled** (включен)

## 🛠️ Если ничего не помогает - создайте новое OAuth приложение

### Шаг 1: Создайте новый OAuth Client ID

1. В Google Cloud Console: **APIs & Services** → **Credentials**
2. Нажмите: **Create Credentials** → **OAuth client ID**
3. Если появится запрос на настройку OAuth consent screen:
   - **User Type**: External
   - **App name**: Calendar Bot
   - **User support email**: ваш email
   - **Developer contact**: ваш email
   - Нажмите **Save and Continue**
   - В **Scopes** добавьте: `https://www.googleapis.com/auth/calendar.readonly`
   - Нажмите **Save and Continue**
   - В **Test users** добавьте: `kolunt@gmail.com`
   - Нажмите **Save and Continue** → **Back to Dashboard**

4. Создайте OAuth client:
   - **Application type**: Web application
   - **Name**: Calendar Bot
   - **Authorized redirect URIs**: 
     ```
     http://localhost:5000/callback/google
     ```
   - Нажмите **Create**

5. Скопируйте:
   - **Client ID** (длинная строка)
   - **Client secret** (строка вида `GOCSPX-...`)

### Шаг 2: Обновите .env файл

Замените в `.env`:
```
GOOGLE_CLIENT_ID=новый_client_id
GOOGLE_CLIENT_SECRET=новый_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback/google
```

### Шаг 3: Перезапустите Flask сервер

После обновления `.env` перезапустите Flask сервер.

## 📋 Чек-лист

- [ ] OAuth consent screen настроен
- [ ] Email `kolunt@gmail.com` добавлен в Test users
- [ ] OAuth 2.0 Client ID существует и активен
- [ ] Redirect URI в Google Console: `http://localhost:5000/callback/google`
- [ ] Redirect URI в `.env`: `http://localhost:5000/callback/google`
- [ ] Google Calendar API включен
- [ ] Flask сервер перезапущен после изменений

## 🎯 После исправления

Попробуйте снова подключить Google Calendar через бота. Ошибка должна исчезнуть.




