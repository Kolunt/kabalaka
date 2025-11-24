"""Модуль для отправки рассылок"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from telegram import Bot
from database import Database
from config import Config
from i18n import SUPPORTED_LANGUAGES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = Database()

async def send_broadcast_async(broadcast_id: int):
    """Асинхронная отправка рассылки"""
    try:
        broadcast = db.get_broadcast(broadcast_id)
        if not broadcast:
            logger.error(f"Рассылка {broadcast_id} не найдена")
            return
        
        if broadcast['status'] != 'pending':
            logger.warning(f"Рассылка {broadcast_id} уже обрабатывается или завершена")
            return
        
        # Обновляем статус на "отправляется"
        db.update_broadcast_status(broadcast_id, 'sending')
        
        # Получаем токен бота
        token = Config.get_telegram_token()
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN не установлен")
            db.update_broadcast_status(broadcast_id, 'failed', 0, 1)
            return
        
        bot = Bot(token=token)
        
        # Получаем список пользователей по языкам
        languages = broadcast.get('languages')
        users = db.get_users_by_languages(languages)
        
        # Устанавливаем общее количество пользователей
        db.set_broadcast_total_users(broadcast_id, len(users))
        
        sent_count = 0
        failed_count = 0
        
        # Отправляем сообщения
        for user in users:
            user_id = user['user_id']
            user_language = user.get('language') or 'en'
            
            # Проверяем, нужно ли отправлять этому пользователю
            if languages and user_language not in languages:
                db.add_broadcast_history(
                    broadcast_id, user_id, user_language, 'skipped',
                    'Язык пользователя не входит в список выбранных'
                )
                continue
            
            try:
                # Отправляем сообщение
                await bot.send_message(chat_id=user_id, text=broadcast['message_text'])
                
                # Записываем в историю
                db.add_broadcast_history(
                    broadcast_id, user_id, user_language, 'sent'
                )
                sent_count += 1
                
                # Небольшая задержка, чтобы не превысить лимиты API
                await asyncio.sleep(0.05)  # 50ms между сообщениями
                
            except Exception as e:
                error_msg = str(e)
                # Улучшаем сообщение об ошибке для пользователя
                if "blocked" in error_msg.lower() or "bot was blocked" in error_msg.lower():
                    error_msg = "Пользователь заблокировал бота"
                elif "chat not found" in error_msg.lower():
                    error_msg = "Чат не найден"
                elif "forbidden" in error_msg.lower():
                    error_msg = "Доступ запрещен"
                
                logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
                
                # Записываем ошибку в историю
                db.add_broadcast_history(
                    broadcast_id, user_id, user_language, 'failed', error_msg
                )
                failed_count += 1
        
        # Обновляем финальный статус
        final_status = 'completed' if failed_count == 0 or sent_count > 0 else 'failed'
        db.update_broadcast_status(broadcast_id, final_status, sent_count, failed_count)
        
        logger.info(f"Рассылка {broadcast_id} завершена: отправлено {sent_count}, ошибок {failed_count}")
        
    except Exception as e:
        logger.error(f"Критическая ошибка при отправке рассылки {broadcast_id}: {e}", exc_info=True)
        db.update_broadcast_status(broadcast_id, 'failed', 0, 1)

def send_broadcast(broadcast_id: int):
    """Синхронная обертка для отправки рассылки"""
    try:
        asyncio.run(send_broadcast_async(broadcast_id))
    except Exception as e:
        logger.error(f"Ошибка при запуске рассылки {broadcast_id}: {e}")

