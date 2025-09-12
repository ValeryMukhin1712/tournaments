#!/usr/bin/env python3
"""
Скрипт для добавления полей start_time и end_time в таблицу tournament
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Добавляет поля start_time и end_time в таблицу tournament"""
    
    db_path = 'instance/tournaments.db'
    
    if not os.path.exists(db_path):
        print(f"База данных {db_path} не найдена!")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существуют ли уже колонки
        cursor.execute("PRAGMA table_info(tournament)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'start_time' in columns and 'end_time' in columns:
            print("Колонки start_time и end_time уже существуют в таблице tournament")
            return True
        
        print("Добавляем колонки start_time и end_time в таблицу tournament...")
        
        # Добавляем колонки с значениями по умолчанию
        cursor.execute("ALTER TABLE tournament ADD COLUMN start_time TIME DEFAULT '09:00'")
        cursor.execute("ALTER TABLE tournament ADD COLUMN end_time TIME DEFAULT '17:00'")
        
        # Обновляем существующие записи с значениями по умолчанию
        cursor.execute("UPDATE tournament SET start_time = '09:00' WHERE start_time IS NULL")
        cursor.execute("UPDATE tournament SET end_time = '17:00' WHERE end_time IS NULL")
        
        # Сохраняем изменения
        conn.commit()
        
        print("✅ Колонки start_time и end_time успешно добавлены!")
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(tournament)")
        columns = cursor.fetchall()
        print("\nТекущая структура таблицы tournament:")
        for column in columns:
            print(f"  {column[1]} ({column[2]})")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при миграции базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🔄 Начинаем миграцию базы данных...")
    success = migrate_database()
    
    if success:
        print("\n✅ Миграция завершена успешно!")
    else:
        print("\n❌ Миграция не удалась!")
