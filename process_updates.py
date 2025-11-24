"""Обработка накопившихся обновлений один раз (для бесплатного тарифа)"""
import asyncio
import logging
import sys
from bot import setup_bot
from config import Config

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def process_updates_once():
    """Обработка накопившихся обновлений один раз и завершение"""
    try:
        logger.info("Обработка накопившихся обновлений...")
        
        # Настройка бота
        application = setup_bot()
        
        # Инициализируем приложение
        await application.initialize()
        
        # Запускаем приложение
        await application.start()
        
        logger.info("Бот инициализирован, обработка обновлений...")
        
        # Получаем и обрабатываем обновления один раз
        try:
            # Используем get_updates для получения накопившихся обновлений
            bot = application.bot
            
            # Получаем последний offset, чтобы обработать все накопившиеся обновления
            updates = await bot.get_updates(
                timeout=5,  # Короткий timeout для получения обновлений
                allowed_updates=None
            )
            
            if updates:
                logger.info(f"Получено {len(updates)} обновлений, обработка...")
                # Обрабатываем обновления через application
                for update in updates:
                    try:
                        await application.process_update(update)
                    except Exception as e:
                        logger.error(f"Ошибка при обработке обновления {update.update_id}: {e}")
                
                # Обновляем offset, чтобы Telegram знал, что обновления обработаны
                if updates:
                    last_update_id = max(u.update_id for u in updates)
                    await bot.get_updates(offset=last_update_id + 1, timeout=0)
                    logger.info(f"Обработано {len(updates)} обновлений, последний offset: {last_update_id + 1}")
            else:
                logger.info("Новых обновлений нет")
                
        except Exception as e:
            logger.error(f"Ошибка при обработке обновлений: {e}", exc_info=True)
        finally:
            # Останавливаем приложение
            await application.stop()
            await application.shutdown()
            
        logger.info("Обработка обновлений завершена")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    try:
        Config.validate()
        # На Windows используем SelectorEventLoop для совместимости
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Обрабатываем обновления один раз
        asyncio.run(process_updates_once())
    except KeyboardInterrupt:
        logger.info("Остановка...")
    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        sys.exit(1)

