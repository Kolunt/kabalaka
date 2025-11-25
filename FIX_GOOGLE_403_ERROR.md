# Исправление ошибки 403 "accessNotConfigured" для Google Calendar

## Проблема

В логах видна ошибка:
```
Encountered 403 Forbidden with reason "accessNotConfigured"
Получено событий из google для пользователя 354932588: 0
```

Это означает, что **Google Calendar API не включен** в вашем проекте Google Cloud Console.

## Решение

### Шаг 1: Включите Google Calendar API

1. Откройте [Google Cloud Console](https://console.cloud.google.com/)
2. Выберите ваш проект (тот, где создан OAuth Client ID)
3. Перейдите в **APIs & Services** → **Library**
4. В поиске введите: **"Google Calendar API"**
5. Нажмите на **Google Calendar API**
6. Нажмите кнопку **"Enable"** (Включить)
7. Дождитесь активации API (обычно несколько секунд)

### Шаг 2: Проверьте OAuth Consent Screen

1. Перейдите в **APIs & Services** → **OAuth consent screen**
2. Убедитесь, что:
   - **User Type**: External (или Internal, если у вас Workspace)
   - **App name**: указано
   - **User support email**: ваш email
   - **Developer contact**: ваш email
   - **Scopes**: должен быть добавлен `https://www.googleapis.com/auth/calendar.readonly`
   - **Test users**: добавлен ваш email (если приложение в режиме тестирования)

### Шаг 3: Переподключите календари

После включения API нужно переподключить календари:

1. Откройте Telegram бота
2. Перейдите в **Календари**
3. Отключите Google Calendar (если подключен)
4. Подключите Google Calendar заново
5. Авторизуйтесь в Google
6. Разрешите доступ к календарю

### Шаг 4: Проверьте работу

1. Создайте тестовое событие в Google Calendar
2. Подождите следующего запуска cron (или вызовите `/test/check-events`)
3. Проверьте логи - ошибка 403 должна исчезнуть

## Проверка

После исправления в логах должно быть:
```
Получено событий из google для пользователя 354932588: X
```
(где X > 0, если есть события)

Вместо:
```
Encountered 403 Forbidden with reason "accessNotConfigured"
Получено событий из google для пользователя 354932588: 0
```

## Дополнительная информация

Если после включения API ошибка сохраняется:
1. Убедитесь, что используете правильный проект (тот, где создан OAuth Client ID)
2. Проверьте, что OAuth Client ID и Client Secret правильные в админ-панели
3. Попробуйте создать новый OAuth Client ID в том же проекте
4. Убедитесь, что прошло достаточно времени после включения API (иногда требуется несколько минут)



