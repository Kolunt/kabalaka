# Последний вариант решения 401: invalid_client

## ⚠️ Если ВСЁ правильно, но ошибка сохраняется

### Критическая проверка

1. **Проверьте проект в Google Cloud Console:**
   - Client ID: `417657561478-jvn4uo36124rphjs6srialklji518ht7.apps.googleusercontent.com`
   - Найдите проект, где создан OAuth приложение с таким Client ID
   - Убедитесь, что вы смотрите в ПРАВИЛЬНЫЙ проект

2. **Проверьте, что OAuth приложение существует:**
   - APIs & Services → Credentials
   - Найдите OAuth 2.0 Client ID, который начинается с `417657561478-...`
   - Если его НЕТ - вы в другом проекте!

3. **Создайте Client Secret заново:**
   - В Google Cloud Console откройте ваш OAuth 2.0 Client ID
   - В разделе "Client secret" нажмите **Reset**
   - Скопируйте НОВЫЙ Client Secret
   - Обновите `.env` файл:
     ```
     GOOGLE_CLIENT_SECRET=новый_client_secret
     ```
   - Перезапустите Flask сервер

4. **Проверьте Redirect URI точность:**
   - В Google Cloud Console в OAuth 2.0 Client ID
   - Authorized redirect URIs должен быть **ТОЧНО**:
     ```
     http://localhost:5000/callback/google
     ```
   - Без пробелов в начале/конце
   - С маленькой буквы `http` (не `HTTP`)

## 🔄 Альтернативное решение

Если ничего не помогает, создайте **НОВЫЙ** проект:

1. В Google Cloud Console создайте **НОВЫЙ** проект
2. Включите Google Calendar API
3. Настройте OAuth consent screen:
   - User Type: External
   - App name: Calendar Bot
   - Scopes: `https://www.googleapis.com/auth/calendar.readonly`
   - Test users: `kolunt@gmail.com`
   - Publishing status: Testing
4. Создайте OAuth 2.0 Client ID:
   - Application type: Web application
   - Name: Calendar Bot
   - Authorized redirect URIs: `http://localhost:5000/callback/google`
5. Скопируйте **НОВЫЕ** Client ID и Client Secret
6. Обновите `.env` файл
7. Перезапустите Flask сервер

## 📋 Финальный чек-лист

- [ ] Правильный проект выбран в Google Cloud Console
- [ ] OAuth 2.0 Client ID существует и активен
- [ ] Client ID точно совпадает: `417657561478-jvn4uo36124rphjs6srialklji518ht7.apps.googleusercontent.com`
- [ ] Client Secret создан заново и обновлен в `.env`
- [ ] Redirect URI в Google Console: `http://localhost:5000/callback/google` (точно)
- [ ] Redirect URI в `.env`: `http://localhost:5000/callback/google` (точно)
- [ ] OAuth consent screen: Testing
- [ ] Test users: `kolunt@gmail.com`
- [ ] Google Calendar API включен
- [ ] Flask сервер перезапущен после изменений

