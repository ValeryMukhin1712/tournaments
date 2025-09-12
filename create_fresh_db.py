#!/usr/bin/env python3
"""
Создание свежей базы данных
"""

import sqlite3
import os

def create_fresh_database():
    """Создает свежую базу данных"""
    
    db_path = 'tournament.db'
    
    # Удаляем старую базу данных
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✅ Старая база данных удалена")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Создаем свежую базу данных...")
        
        # Создаем таблицу user
        cursor.execute('''
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                email VARCHAR(120) UNIQUE NOT NULL,
                password_hash VARCHAR(128) NOT NULL,
                role VARCHAR(20) DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу tournament с полями start_time и end_time
        cursor.execute('''
            CREATE TABLE tournament (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) NOT NULL,
                sport_type VARCHAR(50) NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                max_participants INTEGER DEFAULT 16,
                court_count INTEGER DEFAULT 2,
                match_duration INTEGER DEFAULT 60,
                break_duration INTEGER DEFAULT 15,
                start_time TIME DEFAULT '09:00',
                end_time TIME DEFAULT '17:00',
                points_win INTEGER DEFAULT 3,
                points_draw INTEGER DEFAULT 1,
                points_loss INTEGER DEFAULT 0,
                points_to_win INTEGER DEFAULT 2,
                sets_to_win INTEGER DEFAULT 2,
                status VARCHAR(20) DEFAULT 'created',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу participant
        cursor.execute('''
            CREATE TABLE participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournament (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE
            )
        ''')
        
        # Создаем таблицу match
        cursor.execute('''
            CREATE TABLE match (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                participant1_id INTEGER NOT NULL,
                participant2_id INTEGER NOT NULL,
                match_date DATE,
                match_time TIME,
                court_number INTEGER,
                match_number INTEGER,
                status VARCHAR(20) DEFAULT 'запланирован',
                winner_id INTEGER,
                score1 INTEGER DEFAULT 0,
                score2 INTEGER DEFAULT 0,
                set1_score1 INTEGER DEFAULT 0,
                set1_score2 INTEGER DEFAULT 0,
                set2_score1 INTEGER DEFAULT 0,
                set2_score2 INTEGER DEFAULT 0,
                set3_score1 INTEGER DEFAULT 0,
                set3_score2 INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournament (id) ON DELETE CASCADE,
                FOREIGN KEY (participant1_id) REFERENCES participant (id) ON DELETE CASCADE,
                FOREIGN KEY (participant2_id) REFERENCES participant (id) ON DELETE CASCADE,
                FOREIGN KEY (winner_id) REFERENCES participant (id) ON DELETE CASCADE
            )
        ''')
        
        # Создаем индексы
        cursor.execute('CREATE INDEX idx_participant_tournament ON participant(tournament_id)')
        cursor.execute('CREATE INDEX idx_match_tournament ON match(tournament_id)')
        cursor.execute('CREATE INDEX idx_match_participants ON match(participant1_id, participant2_id)')
        
        # Создаем администратора
        cursor.execute('''
            INSERT INTO user (username, email, password_hash, role)
            VALUES ('admin', 'admin@example.com', 'pbkdf2:sha256:600000$8d9f8a8b8c8d8e8f$1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef', 'admin')
        ''')
        
        conn.commit()
        
        # Проверяем структуру
        cursor.execute("PRAGMA table_info(tournament)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        print("✅ База данных создана!")
        print(f"Колонки в tournament: {column_names}")
        
        if 'start_time' in column_names and 'end_time' in column_names:
            print("✅ Поля start_time и end_time найдены!")
            return True
        else:
            print("❌ Поля start_time и end_time не найдены!")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    success = create_fresh_database()
    
    if success:
        print("\n✅ Свежая база данных готова!")
    else:
        print("\n❌ Не удалось создать базу данных!")
