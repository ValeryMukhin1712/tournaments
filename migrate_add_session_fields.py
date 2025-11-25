#!/usr/bin/env python3
"""
Миграция для добавления полей управления сессиями в таблицу user_activity
"""

import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Выполняет миграцию базы данных"""
    
    db_path = 'instance/tournament.db'
    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Начинаем миграцию базы данных...")
        
        # Проверяем существующие колонки
        cursor.execute("PRAGMA table_info(user_activity)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"Существующие колонки: {existing_columns}")
        
        # Добавляем новые колонки, если их еще нет
        new_columns = [
            ('login_token', 'VARCHAR(100)'),
            ('email', 'VARCHAR(100)'),
            ('expires_at', 'DATETIME'),
            ('is_terminated', 'BOOLEAN DEFAULT 0'),
            ('terminated_by', 'VARCHAR(100)'),
            ('terminated_at', 'DATETIME'),
            ('session_duration', 'INTEGER'),
            ('logout_reason', 'VARCHAR(50)'),
            ('pages_visited_count', 'INTEGER DEFAULT 0'),
            ('last_page', 'VARCHAR(200)')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    alter_sql = f"ALTER TABLE user_activity ADD COLUMN {column_name} {column_type}"
                    cursor.execute(alter_sql)
                    print(f"✓ Добавлена колонка: {column_name}")
                except sqlite3.Error as e:
                    print(f"✗ Ошибка при добавлении колонки {column_name}: {e}")
            else:
                print(f"- Колонка {column_name} уже существует")
        
        # Создаем индексы для оптимизации запросов
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_user_activity_email ON user_activity(email)",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_login_token ON user_activity(login_token)",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_is_active ON user_activity(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_last_activity ON user_activity(last_activity)",
            "CREATE INDEX IF NOT EXISTS idx_user_activity_expires_at ON user_activity(expires_at)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                print(f"✓ Создан индекс")
            except sqlite3.Error as e:
                print(f"✗ Ошибка при создании индекса: {e}")
        
        # Обновляем существующие записи
        cursor.execute("""
            UPDATE user_activity 
            SET is_terminated = 0, 
                pages_visited_count = 0,
                logout_reason = 'unknown'
            WHERE is_terminated IS NULL
        """)
        
        conn.commit()
        print("✓ Миграция завершена успешно!")
        
        # Показываем структуру обновленной таблицы
        cursor.execute("PRAGMA table_info(user_activity)")
        columns = cursor.fetchall()
        print("\nОбновленная структура таблицы user_activity:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        return True
        
    except sqlite3.Error as e:
        print(f"✗ Ошибка при миграции: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Миграция выполнена успешно!")
    else:
        print("\n❌ Миграция завершилась с ошибками!")
























