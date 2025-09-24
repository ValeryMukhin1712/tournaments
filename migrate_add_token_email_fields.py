#!/usr/bin/env python3
"""
Миграция для добавления полей отслеживания статуса отправки email в таблицу токенов
"""

import sqlite3
import os
from datetime import datetime

def migrate_token_table():
    """Добавляет поля для отслеживания статуса отправки email в таблицу tokens"""
    
    # Путь к базе данных
    db_path = 'instance/tournament.db'
    if not os.path.exists(db_path):
        db_path = 'tournament.db'
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📊 Подключение к базе данных: {db_path}")
        
        # Проверяем существование таблицы tokens
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'")
        if not cursor.fetchone():
            print("❌ Таблица 'tokens' не найдена")
            return False
        
        # Проверяем, существуют ли уже новые поля
        cursor.execute("PRAGMA table_info(tokens)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_fields = [
            ('email_sent', 'BOOLEAN DEFAULT 0'),
            ('email_sent_at', 'DATETIME'),
            ('email_status', 'VARCHAR(50) DEFAULT "pending"')
        ]
        
        fields_to_add = []
        for field_name, field_type in new_fields:
            if field_name not in columns:
                fields_to_add.append((field_name, field_type))
                print(f"➕ Добавляем поле: {field_name} {field_type}")
            else:
                print(f"✅ Поле уже существует: {field_name}")
        
        if not fields_to_add:
            print("✅ Все поля уже существуют, миграция не требуется")
            return True
        
        # Добавляем новые поля
        for field_name, field_type in fields_to_add:
            try:
                cursor.execute(f"ALTER TABLE tokens ADD COLUMN {field_name} {field_type}")
                print(f"✅ Поле {field_name} добавлено успешно")
            except sqlite3.Error as e:
                print(f"❌ Ошибка при добавлении поля {field_name}: {e}")
                return False
        
        # Обновляем существующие записи
        cursor.execute("UPDATE tokens SET email_status = 'pending' WHERE email_status IS NULL")
        cursor.execute("UPDATE tokens SET email_sent = 0 WHERE email_sent IS NULL")
        
        # Подсчитываем обновленные записи
        cursor.execute("SELECT COUNT(*) FROM tokens")
        total_tokens = cursor.fetchone()[0]
        
        print(f"✅ Обновлено {total_tokens} записей токенов")
        
        # Сохраняем изменения
        conn.commit()
        print("✅ Миграция завершена успешно")
        
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка базы данных: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Запуск миграции для добавления полей email в таблицу токенов")
    print("=" * 60)
    
    success = migrate_token_table()
    
    print("=" * 60)
    if success:
        print("🎉 Миграция выполнена успешно!")
    else:
        print("💥 Миграция завершилась с ошибками!")
