#!/usr/bin/env python3
"""
Скрипт для принудительного обновления схемы базы данных
"""

from app import app, db
from models import create_models

def force_update_schema():
    """Принудительно обновляет схему базы данных"""
    
    with app.app_context():
        try:
            print("🔄 Принудительно обновляем схему базы данных...")
            
            # Создаем все таблицы (это обновит схему)
            db.create_all()
            
            print("✅ Схема базы данных обновлена!")
            
            # Проверяем, что колонки существуют
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('tournament')]
            
            print(f"Колонки в таблице tournament: {columns}")
            
            if 'start_time' in columns and 'end_time' in columns:
                print("✅ Поля start_time и end_time найдены в базе данных!")
                return True
            else:
                print("❌ Поля start_time и end_time не найдены!")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при обновлении схемы: {e}")
            return False

if __name__ == "__main__":
    success = force_update_schema()
    
    if success:
        print("\n✅ Схема базы данных успешно обновлена!")
    else:
        print("\n❌ Не удалось обновить схему базы данных!")
