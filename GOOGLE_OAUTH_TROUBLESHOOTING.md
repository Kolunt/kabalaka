# Устранение ошибки "OAuth client was not found" (401: invalid_client)

## Проблема
Ошибка `Error 401: invalid_client` означает, что Google не может найти OAuth приложение с указанными credentials.

## Возможные причины и решения

### 1. Неправильный Redirect URI

**Проблема:** Redirect URI в `.env` не совпадает с тем, что указан в Google Cloud Console.

**Решение:**
1. Проверьте текущий redirect URI в `.env`:
   ```
   GOOGLE_REDIRECT_URI=http://localhost:5000/callback/google
   ```
   ⚠️ **Важно:** Порт должен быть **5000**, а не 8080!

2. В Google Cloud Console (https://console.cloud.google.com/):
   - Перейдите: APIs & Services → Credentials
   - Найдите ваш OAuth 2.0 Client ID
   - В разделе "Authorized redirect URIs" должно быть **точно**:
     ```
     http://localhost:5000/callback/google
     ```
   - Если там указан другой URI (например, `localhost:8080`), измените на `localhost:5000`
   - Сохраните изменения

### 2. Неправильный Client ID или Client Secret

**Проблема:** Client ID или Client Secret скопированы неправильно.

**Решение:**
1. В Google Cloud Console:
   - Перейдите: APIs & Services → Credentials
   - Найдите ваш OAuth 2.0 Client ID
   - Нажмите на него для просмотра деталей
   - Скопируйте **Client ID** (длинная строка, начинается с цифр)
   - Скопируйте **Client secret** (строка вида `GOCSPX-...`)

2. В `.env` файле проверьте:
   ```
   GOOGLE_CLIENT_ID=ваш_client_id_без_пробелов
   GOOGLE_CLIENT_SECRET=ваш_client_secret_без_пробелов
   ```
   ⚠️ Убедитесь, что нет лишних пробелов или символов!

### 3. OAuth приложение не создано или удалено

**Проблема:** OAuth приложение не существует в Google Cloud Console.

**Решение:**
1. Перейдите: https://console.cloud.google.com/
2. Выберите правильный проект
3. Перейдите: APIs & Services → Credentials
4. Если нет OAuth 2.0 Client ID:
   - Нажмите "Create Credentials" → "OAuth client ID"
   - Если нужно, настройте OAuth consent screen:
     - Application type: **Web application**
     - Name: Calendar Bot
     - Authorized redirect URIs: `http://localhost:5000/callback/google`
   - Скопируйте Client ID и Client Secret

### 4. Не включен Google Calendar API

**Проблема:** Google Calendar API не включен в проекте.

**Решение:**
1. Перейдите: https://console.cloud.google.com/
2. APIs & Services → Library
3. Найдите "Google Calendar API"
4. Нажмите "Enable" (если не включен)

### 5. Проверка текущей конфигурации

Запустите в терминале:
```bash
python -c "from config import Config; print('Client ID:', Config.GOOGLE_CLIENT_ID[:20] + '...'); print('Client Secret:', Config.GOOGLE_CLIENT_SECRET[:10] + '...'); print('Redirect URI:', Config.GOOGLE_REDIRECT_URI)"
```

Убедитесь, что:
- Client ID начинается с цифр (например, `730550260978-...`)
- Client Secret начинается с `GOCSPX-`
- Redirect URI: `http://localhost:5000/callback/google`

### 6. После исправления

1. Перезапустите Flask сервер
2. Попробуйте снова подключить Google Calendar через бота
3. Если ошибка сохраняется, проверьте логи Flask сервера

## Быстрая проверка

1. ✅ Client ID и Client Secret в `.env` правильные
2. ✅ Redirect URI в `.env`: `http://localhost:5000/callback/google`
3. ✅ Redirect URI в Google Console: `http://localhost:5000/callback/google` (точно такой же!)
4. ✅ Google Calendar API включен
5. ✅ Flask сервер работает на порту 5000
6. ✅ После изменений перезапущен Flask сервер

## Если ничего не помогает

1. Создайте новый OAuth 2.0 Client ID в Google Cloud Console
2. Используйте новые Client ID и Client Secret
3. Убедитесь, что redirect URI указан правильно в обоих местах

