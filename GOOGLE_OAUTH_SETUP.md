# Настройка Google OAuth для Calendar Bot

## Пошаговая инструкция

### Шаг 1: Создание проекта в Google Cloud Console

1. Перейдите на [Google Cloud Console](https://console.cloud.google.com/)
2. Войдите в свой аккаунт Google
3. Нажмите на выпадающий список проектов вверху
4. Нажмите "Новый проект"
5. Введите название проекта (например, "Kabalaka")
6. Нажмите "Создать"

### Шаг 2: Включение Google Calendar API

1. В меню слева выберите "APIs & Services" → "Library"
2. В поиске введите "Google Calendar API"
3. Нажмите на "Google Calendar API"
4. Нажмите кнопку "Enable" (Включить)

### Шаг 3: Создание OAuth 2.0 Credentials

1. Перейдите в "APIs & Services" → "Credentials"
2. Нажмите "Create Credentials" → "OAuth client ID"
3. Если появится запрос на настройку OAuth consent screen:
   - Выберите "External" (для тестирования)
   - Заполните обязательные поля:
     - App name: Kabalaka
     - User support email: ваш email
     - Developer contact information: ваш email
   - Нажмите "Save and Continue"
   - На шаге "Scopes" нажмите "Add or Remove Scopes"
   - Найдите и добавьте: `https://www.googleapis.com/auth/calendar.readonly`
   - Нажмите "Update" → "Save and Continue"
   - На шаге "Test users" добавьте свой email
   - Нажмите "Save and Continue" → "Back to Dashboard"

4. Теперь создайте OAuth client ID:
   - Application type: "Web application"
   - Name: Kabalaka
   - Authorized redirect URIs: 
     - Для локальной разработки: `http://localhost:5000/callback/google`
     - Для PythonAnywhere: `https://yourusername.pythonanywhere.com/callback/google`
   - Нажмите "Create"

5. Скопируйте:
   - **Client ID** (длинная строка, начинается с цифр)
   - **Client secret** (секретный ключ)

### Шаг 4: Настройка в проекте

1. Откройте файл `.env` в корне проекта
2. Добавьте или обновите следующие строки:
   ```
   GOOGLE_CLIENT_ID=ваш_client_id_здесь
   GOOGLE_CLIENT_SECRET=ваш_client_secret_здесь
   GOOGLE_REDIRECT_URI=http://localhost:5000/callback/google
   ```

3. Сохраните файл

### Шаг 5: Проверка

1. Перезапустите Flask сервер (если он запущен)
2. Попробуйте подключить Google Calendar через бота
3. Должна открыться страница авторизации Google

## Важные замечания

- **Redirect URI должен точно совпадать** с тем, что указано в Google Cloud Console
- Для локальной разработки используйте `http://localhost:5000/callback/google`
- Для продакшена на PythonAnywhere используйте `https://yourusername.pythonanywhere.com/callback/google`
- Client ID и Client Secret должны быть из одного и того же OAuth приложения

## Решение проблем

### Ошибка "invalid_client"
- Проверьте, что Client ID и Client Secret скопированы правильно
- Убедитесь, что нет лишних пробелов в `.env` файле
- Проверьте, что redirect URI совпадает в Google Console и в `.env`

### Ошибка "redirect_uri_mismatch"
- Убедитесь, что redirect URI в Google Console точно совпадает с тем, что в `.env`
- Проверьте, что используется правильный порт (5000 для локальной разработки)

### Ошибка "access_denied"
- Убедитесь, что вы добавили свой email в "Test users" в OAuth consent screen
- Проверьте, что приложение не находится в режиме "In production" (для тестирования должно быть "Testing")

