"""Главный файл для локального запуска"""
import asyncio
import logging
from telegram import Update
from bot import setup_bot
from scheduler import check_and_notify_events
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция"""
    logger.info("Запуск Calendar Alarm Bot...")
    
    # Настройка бота
    application = setup_bot()
    
    # Настройка планировщика
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_and_notify_events,
        'interval',
        minutes=Config.CHECK_INTERVAL_MINUTES,
        id='check_events',
        replace_existing=True
    )
    scheduler.start()
    
    logger.info("Бот запущен и готов к работе!")
    
    # Запуск бота
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота...")

