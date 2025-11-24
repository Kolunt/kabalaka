# Проверка Google OAuth конфигурации

## ✅ Исправлено в .env файле

Redirect URI изменен на: `http://localhost:5000/callback/google`

## ⚠️ ВАЖНО: Проверьте Google Cloud Console

Теперь нужно убедиться, что в Google Cloud Console тоже указан правильный redirect URI:

1. Откройте: https://console.cloud.google.com/
2. Перейдите: **APIs & Services** → **Credentials**
3. Найдите ваш OAuth 2.0 Client ID (начинается с `730550260978-...`)
4. Нажмите на него для редактирования
5. В разделе **"Authorized redirect URIs"** должно быть:
   ```
   http://localhost:5000/callback/google
   ```
6. Если там указан другой URI (например, `localhost:8080`), **измените на `localhost:5000`**
7. Нажмите **"Save"**

## После исправления

1. **Перезапустите Flask сервер** (если он запущен)
2. Попробуйте снова подключить Google Calendar через бота
3. Ошибка "OAuth client was not found" должна исчезнуть

## Текущая конфигурация

- ✅ Client ID: `730550260978-...` (правильный формат)
- ✅ Client Secret: `GOCSPX-...` (правильный формат)
- ✅ Redirect URI: `http://localhost:5000/callback/google` (исправлено)

## Если ошибка сохраняется

1. Убедитесь, что в Google Cloud Console redirect URI точно совпадает: `http://localhost:5000/callback/google`
2. Проверьте, что нет лишних пробелов в Client ID и Client Secret в `.env`
3. Убедитесь, что Google Calendar API включен в проекте
4. Перезапустите Flask сервер после всех изменений

