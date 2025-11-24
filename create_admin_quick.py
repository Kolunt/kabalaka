"""Быстрое создание администратора"""
from database import Database
import hashlib

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_admin_quick(username: str, password: str):
    """Быстрое создание администратора"""
    db = Database()
    
    # Проверяем, не существует ли уже такой администратор
    existing = db.get_admin(username)
    if existing:
        print(f"[!] Администратор с именем '{username}' уже существует")
        return False
    
    password_hash = hash_password(password)
    db.create_admin(username, password_hash)
    
    print(f"[OK] Администратор '{username}' успешно создан!")
    return True

if __name__ == '__main__':
    # Создаем администратора admin/admin123
    create_admin_quick('admin', 'admin123')
    print("\nТеперь вы можете войти в админ панель:")
    print("URL: http://localhost:5000/admin/login")
    print("Логин: admin")
    print("Пароль: admin123")

