"""
Инициализация базы данных
"""
from flask_sqlalchemy import SQLAlchemy

# Создаем единый экземпляр SQLAlchemy
db = SQLAlchemy()
