"""
Утилита для генерации QR-кодов для подключения к Telegram боту
"""
import qrcode
import io
import base64
import secrets
from config import Config


def generate_telegram_token():
    """
    Генерирует уникальный токен для привязки пользователя к Telegram боту
    
    Returns:
        str: Уникальный токен длиной 32 символа
    """
    return secrets.token_urlsafe(32)


def generate_qr_code(token: str, bot_username: str = None) -> str:
    """
    Генерирует QR-код с Telegram Deep Link для привязки пользователя к боту
    
    Args:
        token: Уникальный токен для идентификации заявки
        bot_username: Username бота (без @). Если не указан, берется из конфига
        
    Returns:
        str: Base64-encoded изображение QR-кода
    """
    # Получаем username бота из конфига или используем дефолтный
    if not bot_username:
        # Извлекаем username бота из токена (если он есть в конфиге)
        # Для примера используем фиксированное имя, в продакшене нужно будет заменить
        bot_username = "Q_uickScore_bot"  # Username вашего Telegram бота
    
    # Формируем Telegram Deep Link
    # Когда пользователь перейдет по этой ссылке, бот получит команду /start <token>
    telegram_link = f"https://t.me/{bot_username}?start={token}"
    
    # Создаем QR-код
    qr = qrcode.QRCode(
        version=1,  # Размер QR-кода (1-40, автоматически увеличивается если нужно)
        error_correction=qrcode.constants.ERROR_CORRECT_L,  # Уровень коррекции ошибок
        box_size=10,  # Размер одного "пикселя" QR-кода
        border=4,  # Толщина рамки (минимум 4)
    )
    
    qr.add_data(telegram_link)
    qr.make(fit=True)
    
    # Создаем изображение QR-кода
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Конвертируем изображение в base64 для передачи в браузер
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    # Кодируем в base64
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{img_base64}"


def get_bot_username():
    """
    Получает username бота из конфигурации или возвращает дефолтный
    
    Returns:
        str: Username бота без @
    """
    # TODO: Добавить BOT_USERNAME в config.py
    # На данный момент используем хардкод
    return "Q_uickScore_bot"  # Username вашего Telegram бота

