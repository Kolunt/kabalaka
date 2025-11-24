"""Скрипт для запуска бота отдельно (для Always-on task на PythonAnywhere)"""
import asyncio
import logging
import sys
from bot import setup_bot
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция для запуска бота"""
    try:
        logger.info("Запуск Calendar Alarm Bot...")
        
        # Настройка бота
        application = setup_bot()
        
        logger.info("Бот запущен и готов к работе!")
        
        # Запуск бота в режиме polling
        # Используем run_polling, который правильно управляет event loop
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=None
        )
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
    except Exception as e:
        logger.error(f"Критическая ошибка в боте: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        Config.validate()
        # На Windows используем SelectorEventLoop для совместимости
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Запускаем бота
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)
