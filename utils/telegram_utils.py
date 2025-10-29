"""
Утилиты для отправки сообщений в Telegram
"""
import requests
import logging
from config import Config

logger = logging.getLogger(__name__)


def send_telegram_message(message: str, telegram_contact: str = None) -> bool:
    """
    Отправляет сообщение в Telegram через Bot API
    
    Args:
        message: Текст сообщения (поддерживает HTML форматирование)
        telegram_contact: Chat ID или @username получателя. Если не указан, 
                         отправляется на chat_id автора из конфигурации
        
    Returns:
        bool: True если отправка успешна, False в противном случае
    """
    try:
        # Получаем настройки из конфигурации
        bot_token = Config.TELEGRAM_BOT_TOKEN
        
        # Определяем получателя
        if telegram_contact:
            # Если указан контакт участника, отправляем ему
            chat_id = telegram_contact
        else:
            # Иначе отправляем автору (для формы обратной связи)
            chat_id = Config.TELEGRAM_CHAT_ID
        
        # Проверяем наличие настроек
        if not bot_token:
            logger.warning(f"❌ Telegram bot token не задан")
            return False
        
        if not chat_id:
            logger.warning(f"❌ Telegram chat ID не указан")
            return False
        
        logger.debug(f"Telegram настройки: Chat ID={chat_id}, Token={'*****' + bot_token[-10:] if len(bot_token) > 10 else '****'}")
        
        # URL для Telegram Bot API
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        # Параметры запроса
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'  # Поддержка HTML форматирования
        }
        
        logger.info(f"Отправка сообщения в Telegram (chat_id: {chat_id})")
        
        # Отправляем запрос (используем data вместо json для совместимости)
        response = requests.post(url, data=payload, timeout=10)
        
        # Проверяем ответ
        if response.status_code == 200:
            logger.info(f"✅ Сообщение успешно отправлено в Telegram (получатель: {chat_id})")
            return True
        else:
            error_info = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            logger.error(f"❌ Ошибка при отправке в Telegram: {response.status_code} - {error_info}")
            
            # Дополнительная информация для популярных ошибок
            if response.status_code == 400:
                logger.error(f"💡 Подсказка: Проверьте правильность chat_id ({chat_id}). Пользователь должен был написать боту первым (/start)")
            elif response.status_code == 403:
                logger.error(f"💡 Подсказка: Бот заблокирован пользователем или пользователь не начал диалог с ботом")
            
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Timeout при отправке сообщения в Telegram")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке запроса в Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"Непредвиденная ошибка при отправке в Telegram: {e}")
        return False

