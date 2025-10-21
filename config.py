"""
Конфигурация приложения
"""
import os
import secrets
from datetime import timedelta

class Config:
    """Базовая конфигурация"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/tournament.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки безопасности
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Настройки CSRF
    WTF_CSRF_TIME_LIMIT = 3600  # Время жизни CSRF токена в секундах (1 час)
    
    # Настройки турнира
    DEFAULT_POINTS_WIN = 3
    DEFAULT_POINTS_DRAW = 1
    DEFAULT_POINTS_LOSS = 0
    DEFAULT_POINTS_TO_WIN = 21
    
    # Настройки email
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@tournament-system.com'
    
    # Настройки EmailJS (для Railway)
    EMAILJS_SERVICE_ID = os.environ.get('EMAILJS_SERVICE_ID')
    EMAILJS_TEMPLATE_ID = os.environ.get('EMAILJS_TEMPLATE_ID')
    EMAILJS_USER_ID = os.environ.get('EMAILJS_USER_ID')
    
    # Настройки управления сессиями
    SESSION_TIMEOUT_HOURS = int(os.environ.get('SESSION_TIMEOUT_HOURS', 2))  # Время жизни сессии
    SESSION_CHECK_INTERVAL = int(os.environ.get('SESSION_CHECK_INTERVAL', 300))  # Интервал проверки сессий (5 минут)
    FORCE_SINGLE_SESSION = os.environ.get('FORCE_SINGLE_SESSION', 'true').lower() in ['true', 'on', '1']  # Строгий режим одной сессии
    ADMIN_SESSION_MANAGEMENT = os.environ.get('ADMIN_SESSION_MANAGEMENT', 'true').lower() in ['true', 'on', '1']  # Включить управление сессиями для админа
    SESSION_HISTORY_RETENTION_DAYS = int(os.environ.get('SESSION_HISTORY_RETENTION_DAYS', 90))  # Хранение истории сессий (дни)
    ENABLE_PAGE_TRACKING = os.environ.get('ENABLE_PAGE_TRACKING', 'true').lower() in ['true', 'on', '1']  # Включить отслеживание страниц

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tournament.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки email для разработки
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = 'tournaments.master@gmail.com'
    MAIL_PASSWORD = 'jqjahujrmrnyzfbo'
    MAIL_DEFAULT_SENDER = 'tournaments.master@gmail.com'

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    # Railway автоматически предоставляет DATABASE_URL для PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Настройки безопасности для продакшена
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
