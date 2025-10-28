"""
Утилиты для отправки сообщений в Telegram
"""
import requests
import logging
from config import Config

logger = logging.getLogger(__name__)


def send_telegram_message(message: str) -> bool:
    """
    Отправляет сообщение в Telegram через Bot API
    
    Args:
        message: Текст сообщения (поддерживает HTML форматирование)
        
    Returns:
        bool: True если отправка успешна, False в противном случае
    """
    try:
        # Получаем настройки из конфигурации
        bot_token = Config.TELEGRAM_BOT_TOKEN
        chat_id = Config.TELEGRAM_CHAT_ID
        
        # Проверяем наличие настроек
        if not bot_token or not chat_id:
            logger.warning(f"❌ Telegram настройки не заданы. Bot token: {'задан' if bot_token else 'НЕ задан'}, Chat ID: {'задан' if chat_id else 'НЕ задан'}")
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
            logger.info("Сообщение успешно отправлено в Telegram")
            return True
        else:
            logger.error(f"Ошибка при отправке в Telegram: {response.status_code} - {response.text}")
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

