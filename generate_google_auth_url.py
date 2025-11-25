"""Скрипт для генерации прямой ссылки авторизации Google"""
import sys
import io
# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from calendar_google import GoogleCalendar
from config import Config
from database import Database

def generate_auth_url(user_id: int = None):
    """Генерация URL для авторизации Google"""
    try:
        # Инициализируем Google Calendar
        google_cal = GoogleCalendar()
        
        # Проверяем, что credentials установлены
        if not google_cal.client_id:
            print("❌ Ошибка: Google Client ID не установлен")
            print("Установите его в админ-панели: Настройки → Основные настройки")
            return None
        
        if not google_cal.redirect_uri:
            print("❌ Ошибка: Google Redirect URI не установлен")
            print("Установите его в админ-панели: Настройки → Основные настройки")
            return None
        
        # Генерируем URL
        auth_url = google_cal.get_authorization_url(user_id=user_id)
        
        print("=" * 80)
        print("🔗 ПРЯМАЯ ССЫЛКА ДЛЯ АВТОРИЗАЦИИ GOOGLE")
        print("=" * 80)
        print()
        print(auth_url)
        print()
        print("=" * 80)
        print("📋 ИНСТРУКЦИЯ:")
        print("=" * 80)
        print("1. Скопируйте ссылку выше")
        print("2. Откройте её в браузере (желательно в режиме инкогнито)")
        print("3. Выберите аккаунт Google для авторизации")
        print("4. После авторизации вы будете перенаправлены на callback URL")
        print("5. Если вы авторизуетесь через Telegram бота, авторизация обработается автоматически")
        print()
        print("⚠️  ВАЖНО:")
        print("- Если user_id указан, он будет передан в параметре 'state'")
        print("- Это позволяет связать авторизацию с конкретным пользователем Telegram")
        print("- Для тестирования можно не указывать user_id")
        print()
        
        return auth_url
        
    except Exception as e:
        print(f"❌ Ошибка при генерации URL: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    # Проверяем аргументы командной строки
    user_id = None
    if len(sys.argv) > 1:
        try:
            user_id = int(sys.argv[1])
            print(f"📱 Используется user_id: {user_id}")
        except ValueError:
            print(f"⚠️  Неверный user_id: {sys.argv[1]}. Используется None")
    
    # Генерируем URL
    url = generate_auth_url(user_id)
    
    if url:
        print("✅ URL успешно сгенерирован!")
    else:
        print("❌ Не удалось сгенерировать URL")
        sys.exit(1)

