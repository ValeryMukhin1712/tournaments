#!/usr/bin/env python3
"""
Миграция для добавления таблицы rally
Таблица для сохранения результатов розыгрышей в бадминтоне
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Rally
from sqlalchemy import text

def migrate_add_rally():
    """Добавляет таблицу rally в базу данных"""
    with app.app_context():
        try:
            # Создаем таблицу rally
            db.create_all()
            print("✅ Таблица rally успешно создана")
            
            # Проверяем, что таблица создана
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='rally'"))
                if result.fetchone():
                    print("✅ Таблица rally существует в базе данных")
                    
                    # Проверяем наличие колонок
                    result = conn.execute(text("PRAGMA table_info('rally')"))
                    columns = [row[1] for row in result.fetchall()]
                    print(f"   Колонки в таблице: {', '.join(columns)}")
                else:
                    print("❌ Таблица rally не найдена")
                    return False
                
        except Exception as e:
            print(f"❌ Ошибка при создании таблицы rally: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    return True

if __name__ == "__main__":
    print("🔄 Запуск миграции для добавления таблицы rally...")
    if migrate_add_rally():
        print("✅ Миграция завершена успешно")
    else:
        print("❌ Миграция завершилась с ошибкой")
        sys.exit(1)

