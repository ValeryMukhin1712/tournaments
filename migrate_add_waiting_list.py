"""
Миграция для добавления таблицы WaitingList
"""
import sqlite3
import os
from datetime import datetime

def migrate_add_waiting_list():
    """Добавляет таблицу WaitingList в базу данных"""
    
    # Путь к базе данных
    db_path = 'instance/tournament.db'
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем, существует ли уже таблица WaitingList
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='waiting_list'
        """)
        
        if cursor.fetchone():
            print("Таблица WaitingList уже существует")
            conn.close()
            return True
        
        # Создаем таблицу WaitingList
        cursor.execute("""
            CREATE TABLE waiting_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                skill_level VARCHAR(50) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR(20) DEFAULT 'ожидает',
                FOREIGN KEY (tournament_id) REFERENCES tournament (id)
            )
        """)
        
        # Создаем индексы для оптимизации
        cursor.execute("""
            CREATE INDEX idx_waiting_list_tournament_id ON waiting_list (tournament_id)
        """)
        
        cursor.execute("""
            CREATE INDEX idx_waiting_list_status ON waiting_list (status)
        """)
        
        # Сохраняем изменения
        conn.commit()
        conn.close()
        
        print("Таблица WaitingList успешно создана")
        return True
        
    except Exception as e:
        print(f"Ошибка при создании таблицы WaitingList: {e}")
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == "__main__":
    migrate_add_waiting_list()
