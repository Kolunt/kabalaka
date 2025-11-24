"""Управление процессом бота"""
import os
import subprocess
import signal
import json
import logging
from pathlib import Path
from typing import Optional, Dict
from telegram import Bot
from config import Config

logger = logging.getLogger(__name__)

BOT_PID_FILE = 'bot.pid'
BOT_SCRIPT = 'run_bot.py'

def get_bot_pid() -> Optional[int]:
    """Получение PID процесса бота"""
    try:
        # Сначала проверяем PID файл
        if os.path.exists(BOT_PID_FILE):
            with open(BOT_PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            # Проверяем, что процесс еще существует
            try:
                if os.name == 'nt':  # Windows
                    import psutil
                    psutil.Process(pid)
                    return pid
                else:  # Unix/Linux
                    os.kill(pid, 0)  # Проверка без отправки сигнала
                    return pid
            except (OSError, psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, ImportError):
                # Процесс не существует, удаляем файл
                try:
                    os.remove(BOT_PID_FILE)
                except OSError:
                    pass
        
        # Если PID файла нет или процесс не найден, ищем по имени скрипта
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any(BOT_SCRIPT in str(arg) for arg in cmdline):
                        real_pid = proc.info['pid']
                        # Сохраняем найденный PID
                        save_bot_pid(real_pid)
                        return real_pid
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except ImportError:
            # psutil не установлен, пропускаем поиск
            pass
    except Exception as e:
        logger.error(f"Ошибка при чтении PID файла: {e}")
    return None

def save_bot_pid(pid: int):
    """Сохранение PID процесса бота"""
    try:
        with open(BOT_PID_FILE, 'w') as f:
            f.write(str(pid))
    except Exception as e:
        logger.error(f"Ошибка при сохранении PID: {e}")

def is_bot_running() -> bool:
    """Проверка, запущен ли бот"""
    pid = get_bot_pid()
    if pid is None:
        return False
    
    # Проверяем, что процесс действительно существует
    try:
        if os.name == 'nt':  # Windows
            # На Windows используем psutil или проверку через tasklist
            try:
                import psutil
                psutil.Process(pid)
                return True
            except (ImportError, psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Если psutil не установлен или процесс не найден, пробуем через subprocess
                result = subprocess.run(
                    ['tasklist', '/FI', f'PID eq {pid}'],
                    capture_output=True,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                return str(pid) in result.stdout
        else:  # Unix/Linux
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.SubprocessError, Exception) as e:
        # Процесс не существует, удаляем PID файл
        logger.debug(f"Процесс {pid} не найден: {e}")
        if os.path.exists(BOT_PID_FILE):
            try:
                os.remove(BOT_PID_FILE)
            except OSError:
                pass
        return False

def stop_bot() -> bool:
    """Остановка бота"""
    pid = get_bot_pid()
    if not pid:
        return False
    
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], 
                         capture_output=True, check=False)
        else:  # Unix/Linux
            os.kill(pid, signal.SIGTERM)
        
        # Удаляем PID файл
        if os.path.exists(BOT_PID_FILE):
            os.remove(BOT_PID_FILE)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при остановке бота: {e}")
        return False

def start_bot() -> Optional[int]:
    """Запуск бота"""
    try:
        # Проверяем, не запущен ли уже бот
        if is_bot_running():
            logger.warning("Бот уже запущен")
            return get_bot_pid()
        
        # Запускаем бота в фоновом режиме
        import sys
        python_exe = sys.executable
        script_path = os.path.abspath(BOT_SCRIPT)
        
        if os.name == 'nt':  # Windows
            # На Windows используем более надежный способ через cmd
            import tempfile
            batch_file = os.path.join(tempfile.gettempdir(), 'start_bot.bat')
            with open(batch_file, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{os.getcwd()}"\n')
                f.write(f'"{python_exe}" "{script_path}"\n')
            
            # Запускаем через cmd в фоне
            process = subprocess.Popen(
                ['cmd', '/c', 'start', '/B', batch_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            # Сохраняем PID родительского процесса
            pid = process.pid
            save_bot_pid(pid)
            logger.info(f"Бот запущен с PID: {pid}")
            
            # Даем время на запуск
            import time
            time.sleep(3)
            
            # Проверяем, что процесс еще работает
            try:
                os.kill(pid, 0)
                return pid
            except OSError:
                # Пробуем найти процесс по имени скрипта
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if proc.info['cmdline'] and BOT_SCRIPT in ' '.join(proc.info['cmdline']):
                            real_pid = proc.info['pid']
                            save_bot_pid(real_pid)
                            return real_pid
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                logger.error("Процесс бота завершился сразу после запуска")
                if os.path.exists(BOT_PID_FILE):
                    os.remove(BOT_PID_FILE)
                return None
        else:  # Unix/Linux
            process = subprocess.Popen(
                ['python3', BOT_SCRIPT],
                stdout=open('bot_stdout.log', 'a'),
                stderr=open('bot_stderr.log', 'a'),
                start_new_session=True,
                cwd=os.getcwd()
            )
            pid = process.pid
            save_bot_pid(pid)
            logger.info(f"Бот запущен с PID: {pid}")
            return pid
    except ImportError:
        # Если psutil не установлен, используем простой способ
        logger.warning("psutil не установлен, используем упрощенный запуск")
        try:
            import sys
            python_exe = sys.executable
            process = subprocess.Popen(
                [python_exe, BOT_SCRIPT],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                stdout=open('bot_stdout.log', 'a'),
                stderr=open('bot_stderr.log', 'a'),
                cwd=os.getcwd()
            )
            pid = process.pid
            save_bot_pid(pid)
            import time
            time.sleep(2)
            try:
                os.kill(pid, 0)
                return pid
            except OSError:
                if os.path.exists(BOT_PID_FILE):
                    os.remove(BOT_PID_FILE)
                return None
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return None

def restart_bot() -> bool:
    """Перезапуск бота"""
    logger.info("Перезапуск бота...")
    stop_bot()
    import time
    time.sleep(2)  # Даем время на остановку
    pid = start_bot()
    return pid is not None

async def check_bot_connection() -> Dict[str, any]:
    """Проверка подключения к боту через Telegram API"""
    try:
        token = Config.get_telegram_token()
        if not token:
            return {
                'success': False,
                'error': 'Токен не установлен'
            }
        
        bot = Bot(token=token)
        bot_info = await bot.get_me()
        
        return {
            'success': True,
            'bot_id': bot_info.id,
            'bot_username': bot_info.username,
            'bot_first_name': bot_info.first_name,
            'is_bot': bot_info.is_bot
        }
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения: {e}")
        return {
            'success': False,
            'error': str(e)
        }

