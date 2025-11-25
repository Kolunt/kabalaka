# Как сформировать прямую ссылку для авторизации Google

## Способ 1: Использование скрипта (рекомендуется)

Самый простой способ - использовать готовый скрипт:

```bash
python generate_google_auth_url.py
```

Это сгенерирует URL с текущими настройками из админ-панели или `.env` файла.

### С указанием user_id (для конкретного пользователя Telegram):

```bash
python generate_google_auth_url.py 123456789
```

Где `123456789` - это ID пользователя Telegram.

## Способ 2: Через Python код

Если нужно получить URL программно:

```python
from calendar_google import GoogleCalendar

# Инициализация
google_cal = GoogleCalendar()

# Генерация URL (без user_id)
auth_url = google_cal.get_authorization_url()

# Или с user_id
auth_url = google_cal.get_authorization_url(user_id=123456789)

print(auth_url)
```

## Способ 3: Формирование URL вручную

Если нужно сформировать URL вручную, используйте следующую структуру:

```
https://accounts.google.com/o/oauth2/auth?
  response_type=code
  &client_id=ВАШ_CLIENT_ID
  &redirect_uri=ВАШ_REDIRECT_URI (URL-encoded)
  &scope=https://www.googleapis.com/auth/calendar.readonly (URL-encoded)
  &state=ОПЦИОНАЛЬНЫЙ_STATE
  &access_type=offline
  &include_granted_scopes=true
  &prompt=consent
```

### Пример:

```
https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=417657561478-xxxxx.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A5000%2Fcallback%2Fgoogle&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcalendar.readonly&access_type=offline&include_granted_scopes=true&prompt=consent
```

### Параметры:

- **response_type**: `code` (всегда)
- **client_id**: Ваш Google Client ID
- **redirect_uri**: URL для перенаправления после авторизации (должен быть URL-encoded)
- **scope**: Права доступа (должен быть URL-encoded)
- **state**: Опциональный параметр для передачи user_id или другой информации
- **access_type**: `offline` (для получения refresh token)
- **include_granted_scopes**: `true` (для включения всех запрошенных прав)
- **prompt**: `consent` (для принудительного показа экрана согласия)

## Использование сгенерированной ссылки

1. Скопируйте сгенерированную ссылку
2. Откройте её в браузере (желательно в режиме инкогнито)
3. Выберите аккаунт Google для авторизации
4. Разрешите доступ к календарю
5. После авторизации вы будете перенаправлены на `redirect_uri` с параметром `code`
6. Если авторизация происходит через Telegram бота, код обработается автоматически

## Важные замечания

- ⚠️ **Redirect URI должен точно совпадать** с тем, что указан в Google Cloud Console
- ⚠️ **Client ID должен быть правильным** и соответствовать вашему проекту
- ⚠️ **Для тестирования** используйте режим инкогнито, чтобы не использовать уже авторизованный аккаунт
- ⚠️ **State параметр** используется для связи авторизации с конкретным пользователем Telegram

## Где взять настройки

Все настройки можно найти в админ-панели:
- **Настройки** → **Основные настройки**
- Или в файле `.env`:
  - `GOOGLE_CLIENT_ID`
  - `GOOGLE_CLIENT_SECRET`
  - `GOOGLE_REDIRECT_URI`

## Отладка

Если ссылка не работает, проверьте:

1. Правильность Client ID в Google Cloud Console
2. Соответствие Redirect URI в ссылке и в Google Cloud Console
3. Статус OAuth Consent Screen (должен быть опубликован или добавлены тестовые пользователи)
4. Включен ли Google Calendar API в проекте



