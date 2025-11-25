#!/usr/bin/env python3
"""
Миграция для добавления таблицы match_log
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, MatchLog

def migrate_add_match_log():
    """Добавляет таблицу match_log в базу данных"""
    with app.app_context():
        try:
            # Создаем таблицу match_log
            db.create_all()
            print("✅ Таблица match_log успешно создана")
            
            # Проверяем, что таблица создана
            result = db.engine.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_log'")
            if result.fetchone():
                print("✅ Таблица match_log существует в базе данных")
            else:
                print("❌ Таблица match_log не найдена")
                
        except Exception as e:
            print(f"❌ Ошибка при создании таблицы match_log: {e}")
            return False
            
    return True

if __name__ == "__main__":
    print("🔄 Запуск миграции для добавления таблицы match_log...")
    if migrate_add_match_log():
        print("✅ Миграция завершена успешно")
    else:
        print("❌ Миграция завершилась с ошибкой")




















