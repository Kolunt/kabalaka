"""Инициализация базы данных"""
from database import Database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_database():
    """Инициализация базы данных"""
    logger.info("Инициализация базы данных...")
    db = Database()
    logger.info("База данных успешно инициализирована!")
    logger.info("Для создания администратора запустите: python create_admin.py")

if __name__ == '__main__':
    init_database()

