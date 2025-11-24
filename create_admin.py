"""Скрипт для создания администратора"""
import sys
import getpass
from database import Database
import hashlib

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin():
    """Создание администратора"""
    db = Database()
    
    print("=" * 50)
    print("Создание администратора для админ панели")
    print("=" * 50)
    
    username = input("Введите имя пользователя: ").strip()
    if not username:
        print("Ошибка: имя пользователя не может быть пустым")
        return
    
    # Проверяем, не существует ли уже такой администратор
    existing = db.get_admin(username)
    if existing:
        print(f"Ошибка: администратор с именем '{username}' уже существует")
        return
    
    password = getpass.getpass("Введите пароль: ")
    if not password:
        print("Ошибка: пароль не может быть пустым")
        return
    
    password_confirm = getpass.getpass("Подтвердите пароль: ")
    if password != password_confirm:
        print("Ошибка: пароли не совпадают")
        return
    
    password_hash = hash_password(password)
    db.create_admin(username, password_hash)
    
    print(f"\n✅ Администратор '{username}' успешно создан!")
    print(f"Теперь вы можете войти в админ панель по адресу: /admin/login")

if __name__ == '__main__':
    try:
        create_admin()
    except KeyboardInterrupt:
        print("\n\nОперация отменена")
        sys.exit(0)
    except Exception as e:
        print(f"\nОшибка: {e}")
        sys.exit(1)

