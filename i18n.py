"""Модуль для интернационализации (i18n)"""
import json
import os
from typing import Dict, Optional
from database import Database

# Поддерживаемые языки
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'ru': 'Russian',
    'es': 'Spanish'
}

# Язык по умолчанию
DEFAULT_LANGUAGE = 'en'

# Загруженные переводы
_translations: Dict[str, Dict[str, str]] = {}

def load_translations():
    """Загружает все переводы из файлов"""
    global _translations
    locales_dir = os.path.join(os.path.dirname(__file__), 'locales')
    
    for lang_code in SUPPORTED_LANGUAGES.keys():
        lang_file = os.path.join(locales_dir, f'{lang_code}.json')
        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                _translations[lang_code] = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Translation file not found: {lang_file}")
            _translations[lang_code] = {}
        except json.JSONDecodeError as e:
            print(f"Error loading translation file {lang_file}: {e}")
            _translations[lang_code] = {}

def get_user_language(user_id: int) -> str:
    """Получает язык пользователя из базы данных"""
    db = Database()
    user = db.get_user(user_id)
    if user and user.get('language'):
        lang = user['language']
        if lang in SUPPORTED_LANGUAGES:
            return lang
    return DEFAULT_LANGUAGE

def set_user_language(user_id: int, language: str):
    """Устанавливает язык пользователя"""
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}")
    db = Database()
    db.update_user_language(user_id, language)

def t(key: str, user_id: Optional[int] = None, language: Optional[str] = None, **kwargs) -> str:
    """
    Получает переведенный текст
    
    Args:
        key: Ключ перевода
        user_id: ID пользователя (для получения его языка)
        language: Явно указанный язык (приоритет над user_id)
        **kwargs: Параметры для форматирования строки
    
    Returns:
        Переведенный текст или ключ, если перевод не найден
    """
    # Определяем язык
    if language:
        lang = language
    elif user_id:
        lang = get_user_language(user_id)
    else:
        lang = DEFAULT_LANGUAGE
    
    # Загружаем переводы, если еще не загружены
    if not _translations:
        load_translations()
    
    # Получаем перевод
    translation = _translations.get(lang, {}).get(key, '')
    
    # Если перевод не найден, пробуем английский
    if not translation and lang != DEFAULT_LANGUAGE:
        translation = _translations.get(DEFAULT_LANGUAGE, {}).get(key, '')
    
    # Если все еще не найден, возвращаем ключ
    if not translation:
        return key
    
    # Форматируем строку с параметрами
    try:
        return translation.format(**kwargs)
    except KeyError:
        # Если не хватает параметров, возвращаем как есть
        return translation

def get_language_name(language_code: str) -> str:
    """Получает название языка по коду"""
    return SUPPORTED_LANGUAGES.get(language_code, language_code)

# Загружаем переводы при импорте модуля
load_translations()

