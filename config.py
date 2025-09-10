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
    
    # Настройки турнира
    DEFAULT_POINTS_WIN = 3
    DEFAULT_POINTS_DRAW = 1
    DEFAULT_POINTS_LOSS = 0
    DEFAULT_POINTS_TO_WIN = 21

class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tournament.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    # Railway автоматически предоставляет DATABASE_URL для PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Настройки безопасности для продакшена
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
