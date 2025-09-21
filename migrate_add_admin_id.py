#!/usr/bin/env python3
"""
Скрипт для добавления поля admin_id в таблицу tournament
"""
import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Добавляет поле admin_id в таблицу tournament"""
    
    db_path = 'instance/tournament.db'
    
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Выполняем миграцию базы данных...")
        
        # Проверяем, существует ли уже поле admin_id
        cursor.execute("PRAGMA table_info(tournament)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'admin_id' in columns:
            print("✅ Поле admin_id уже существует в таблице tournament")
            return True
        
        # Добавляем поле admin_id
        print("➕ Добавляем поле admin_id в таблицу tournament...")
        cursor.execute("ALTER TABLE tournament ADD COLUMN admin_id INTEGER")
        
        # Создаем индекс для улучшения производительности
        print("🔍 Создаем индекс для поля admin_id...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tournament_admin_id ON tournament(admin_id)")
        
        # Сохраняем изменения
        conn.commit()
        print("✅ Миграция завершена успешно!")
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(tournament)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Текущие поля таблицы tournament: {', '.join(columns)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции: {e}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 МИГРАЦИЯ БАЗЫ ДАННЫХ - ДОБАВЛЕНИЕ admin_id")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("🎉 Миграция завершена успешно!")
    else:
        print("💥 Миграция завершилась с ошибкой!")
    
    print("=" * 60)

