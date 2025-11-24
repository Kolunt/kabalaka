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
            updates = await bot.get_updates(
                offset=-1,  # Получаем последнее обновление
                timeout=1,  # Короткий timeout
                allowed_updates=None
            )
            
            if updates:
                logger.info(f"Получено {len(updates)} обновлений")
                # Обрабатываем обновления через application
                for update in updates:
                    await application.process_update(update)
                    # Обновляем offset для следующего запроса
                    if update.update_id:
                        await bot.get_updates(offset=update.update_id + 1, timeout=0)
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

