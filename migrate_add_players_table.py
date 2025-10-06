#!/usr/bin/env python3
"""
Миграция для добавления таблицы players
"""
import sqlite3
import os
from datetime import datetime

def migrate_add_players_table():
    """Добавляет таблицу players в базу данных"""
    
    # Путь к базе данных
    db_path = 'instance/tournament.db'
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже таблица players
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='player'
        """)
        
        if cursor.fetchone():
            print("Таблица player уже существует")
            return True
        
        # Создаем таблицу player
        cursor.execute("""
            CREATE TABLE player (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем индекс для быстрого поиска по имени
        cursor.execute("""
            CREATE INDEX idx_player_name ON player(name)
        """)
        
        # Создаем индекс для сортировки по времени последнего использования
        cursor.execute("""
            CREATE INDEX idx_player_last_used ON player(last_used_at)
        """)
        
        # Сохраняем изменения
        conn.commit()
        
        print("Таблица player успешно создана")
        print("Индексы созданы:")
        print("- idx_player_name: для поиска по имени")
        print("- idx_player_last_used: для сортировки по времени использования")
        
        return True
        
    except Exception as e:
        print(f"Ошибка при создании таблицы player: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Запуск миграции для добавления таблицы players...")
    success = migrate_add_players_table()
    
    if success:
        print("Миграция завершена успешно!")
    else:
        print("Миграция завершена с ошибками!")

