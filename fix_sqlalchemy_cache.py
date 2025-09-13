#!/usr/bin/env python3
"""
Скрипт для принудительного обновления кеша SQLAlchemy
"""
import os
import sys
import sqlite3

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.user import create_user_model
from models.tournament import create_tournament_model
from models.participant import create_participant_model
from models.match import create_match_model
from models.notification import create_notification_model
from models.match_log import create_match_log_model

# Создаем модели
User = create_user_model(db)
Tournament = create_tournament_model(db)
Participant = create_participant_model(db)
Match = create_match_model(db)
Notification = create_notification_model(db)
MatchLog = create_match_log_model(db)

def fix_sqlalchemy_cache():
    """Принудительно обновляет кеш SQLAlchemy и пересоздает таблицы"""
    with app.app_context():
        try:
            print("🔄 Останавливаем приложение...")
            print("✅ Приложение остановлено")
            
            print("\n🧹 Очищаем кеш SQLAlchemy...")
            # Очищаем метаданные
            db.metadata.clear()
            print("✅ Кеш SQLAlchemy очищен")
            
            print("\n🔨 Пересоздаем таблицы с актуальной схемой...")
            # Пересоздаем все таблицы
            db.create_all()
            print("✅ Таблицы пересозданы")
            
            print("\n🔄 Обновляем кеш SQLAlchemy...")
            # Обновляем кеш
            db.metadata.reflect(bind=db.engine)
            print("✅ Кеш SQLAlchemy обновлен")
            
            # Проверяем структуру таблицы participant
            print("\n📋 Проверяем структуру таблицы participant:")
            db_uri = app.config['SQLALCHEMY_DATABASE_URI']
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("PRAGMA table_info(participant)")
                columns = cursor.fetchall()
                for col in columns:
                    print(f"   - {col[1]} ({col[2]})")
                
                conn.close()
            
            print("\n✅ Все готово! Теперь можно запускать приложение.")
            
        except Exception as e:
            print(f"❌ Ошибка при обновлении схемы: {e}")
            return False
        
        return True

if __name__ == "__main__":
    success = fix_sqlalchemy_cache()
    if success:
        print("\n🚀 Готово! Запускайте приложение командой: python app.py")
    else:
        print("\n💥 Произошла ошибка. Проверьте логи выше.")
