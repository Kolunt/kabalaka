#!/usr/bin/env python3
"""Скрипт для автоматического обновления версии проекта"""

import re
import sys

def read_version():
    """Читает текущую версию из VERSION файла"""
    try:
        with open('VERSION', 'r', encoding='utf-8') as f:
            version = f.read().strip()
        return version
    except FileNotFoundError:
        return "0.0.0"

def write_version(version):
    """Записывает версию в VERSION файл и __init__.py"""
    # Обновляем VERSION
    with open('VERSION', 'w', encoding='utf-8') as f:
        f.write(version + '\n')
    
    # Обновляем __init__.py
    try:
        with open('__init__.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Заменяем версию в __init__.py
        content = re.sub(
            r'__version__\s*=\s*["\'][^"\']+["\']',
            f'__version__ = "{version}"',
            content
        )
        
        with open('__init__.py', 'w', encoding='utf-8') as f:
            f.write(content)
    except FileNotFoundError:
        # Создаем __init__.py если его нет
        with open('__init__.py', 'w', encoding='utf-8') as f:
            f.write(f'"""Calendar Alarm Bot"""\n__version__ = "{version}"\n')

def bump_version(version):
    """Увеличивает версию на 0.0.1 (patch)"""
    parts = version.split('.')
    if len(parts) != 3:
        raise ValueError(f"Неверный формат версии: {version}. Ожидается X.Y.Z")
    
    major, minor, patch = map(int, parts)
    patch += 1
    
    return f"{major}.{minor}.{patch}"

def main():
    current_version = read_version()
    print(f"Текущая версия: {current_version}")
    
    new_version = bump_version(current_version)
    print(f"Новая версия: {new_version}")
    
    write_version(new_version)
    print(f"✓ Версия обновлена до {new_version}")
    
    return new_version

if __name__ == '__main__':
    try:
        new_version = main()
        sys.exit(0)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

