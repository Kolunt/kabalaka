"""Обработка накопившихся обновлений один раз (для бесплатного тарифа)"""
import asyncio
import logging
import sys
from bot import setup_bot
from config import Config
from database import Database

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
    db = Database()
    last_offset = None
    
    try:
        logger.info("Обработка накопившихся обновлений...")
        
        # Получаем сохраненный offset из БД
        try:
            offset_str = db.get_system_setting('bot_last_offset')
            if offset_str:
                last_offset = int(offset_str)
                logger.info(f"Используется сохраненный offset: {last_offset}")
        except (ValueError, TypeError):
            pass
        
        # Настройка бота
        application = setup_bot()
        
        # Инициализируем приложение
        await application.initialize()
        
        # Запускаем приложение
        await application.start()
        
        logger.info("Бот инициализирован, обработка обновлений...")
        
        # Получаем и обрабатываем обновления один раз
        try:
            bot = application.bot
            processed_count = 0
            max_updates_per_batch = 100  # Ограничение на количество обновлений за раз
            
            # Обрабатываем обновления батчами, пока они есть
            while True:
                # Получаем обновления с сохраненным offset
                updates = await bot.get_updates(
                    offset=last_offset + 1 if last_offset else None,
                    timeout=10,  # Увеличенный timeout для получения большего количества обновлений
                    allowed_updates=None,
                    limit=100  # Максимум обновлений за запрос
                )
                
                if not updates:
                    break
                
                logger.info(f"Получено {len(updates)} обновлений, обработка...")
                
                # Обрабатываем обновления параллельно для ускорения
                async def process_update_safe(update):
                    try:
                        await application.process_update(update)
                        return True
                    except Exception as e:
                        logger.error(f"Ошибка при обработке обновления {update.update_id}: {e}", exc_info=True)
                        return False
                
                # Обрабатываем обновления параллельно (но не все сразу, батчами по 10)
                batch_size = 10
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i + batch_size]
                    results = await asyncio.gather(*[process_update_safe(u) for u in batch], return_exceptions=True)
                    processed_count += sum(1 for r in results if r is True)
                
                # Обновляем offset
                if updates:
                    last_update_id = max(u.update_id for u in updates)
                    last_offset = last_update_id
                    # Сохраняем offset в БД
                    db.set_system_setting('bot_last_offset', str(last_offset))
                    logger.info(f"Обработано {len(updates)} обновлений, offset обновлен: {last_offset}")
                
                # Если обработали максимум, делаем паузу перед следующим батчем
                if processed_count >= max_updates_per_batch:
                    logger.info(f"Достигнут лимит обработки ({max_updates_per_batch}), останавливаемся")
                    break
                
                # Небольшая пауза перед следующим запросом
                await asyncio.sleep(0.1)
            
            if processed_count == 0:
                logger.info("Новых обновлений нет")
            else:
                logger.info(f"Всего обработано {processed_count} обновлений")
                
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

