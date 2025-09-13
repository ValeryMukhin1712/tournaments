#!/usr/bin/env python3
"""
Скрипт для принудительного обновления схемы SQLAlchemy
"""
import os
import sys
import sqlite3

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.user import User
from models.tournament import Tournament
from models.participant import Participant
from models.match import Match
from models.notification import Notification
from models.match_log import MatchLog

def refresh_sqlalchemy_schema():
    """Принудительно обновляет схему SQLAlchemy"""
    with app.app_context():
        try:
            print("🔄 Обновляем схему SQLAlchemy...")
            
            # Очищаем метаданные
            db.metadata.clear()
            
            # Пересоздаем все таблицы
            db.create_all()
            
            print("✅ Схема SQLAlchemy обновлена!")
            
            # Проверяем структуру таблицы participant
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(participant)")
                columns = cursor.fetchall()
                print(f"\n📋 Структура таблицы participant:")
                for col in columns:
                    print(f"   - {col[1]} ({col[2]})")
                
                conn.close()
            
        except Exception as e:
            print(f"❌ Ошибка при обновлении схемы: {e}")

if __name__ == "__main__":
    refresh_sqlalchemy_schema()

