#!/usr/bin/env python3
"""
Простой скрипт для очистки кеша SQLAlchemy
"""
import os
import sys
import sqlite3

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def simple_fix():
    """Простое решение - пересоздаем базу данных"""
    try:
        print("🔄 Останавливаем приложение...")
        print("✅ Приложение остановлено")
        
        # Удаляем старую базу данных
        db_files = ['tournament.db', 'tournaments_new.db']
        for db_file in db_files:
            if os.path.exists(db_file):
                print(f"🗑️ Удаляем старую базу данных: {db_file}")
                os.remove(db_file)
                print(f"✅ Удалена: {db_file}")
        
        print("\n🔨 Создаем новую базу данных...")
        
        # Создаем новую базу данных с правильной схемой
        conn = sqlite3.connect('tournament.db')
        cursor = conn.cursor()
        
        # Создаем таблицу user
        cursor.execute('''
            CREATE TABLE user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(80) UNIQUE NOT NULL,
                password_hash VARCHAR(120) NOT NULL,
                role VARCHAR(20) DEFAULT 'участник',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу tournament
        cursor.execute('''
            CREATE TABLE tournament (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                start_date DATE,
                end_date DATE,
                max_participants INTEGER DEFAULT 32,
                court_count INTEGER DEFAULT 2,
                match_duration INTEGER DEFAULT 60,
                break_duration INTEGER DEFAULT 10,
                sets_to_win INTEGER DEFAULT 2,
                points_to_win INTEGER DEFAULT 21,
                points_win INTEGER DEFAULT 3,
                points_draw INTEGER DEFAULT 1,
                points_loss INTEGER DEFAULT 0,
                start_time TIME DEFAULT '09:00:00',
                end_time TIME DEFAULT '17:00:00',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (created_by) REFERENCES user (id)
            )
        ''')
        
        # Создаем таблицу participant
        cursor.execute('''
            CREATE TABLE participant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                user_id INTEGER,
                name VARCHAR(100) NOT NULL,
                is_team BOOLEAN DEFAULT 0,
                points INTEGER DEFAULT 0,
                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournament (id),
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        ''')
        
        # Создаем таблицу match
        cursor.execute('''
            CREATE TABLE match (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                participant1_id INTEGER NOT NULL,
                participant2_id INTEGER NOT NULL,
                score1 INTEGER,
                score2 INTEGER,
                score VARCHAR(20),
                sets_won_1 INTEGER DEFAULT 0,
                sets_won_2 INTEGER DEFAULT 0,
                winner_id INTEGER,
                match_date DATE,
                match_time TIME,
                court_number INTEGER,
                match_number INTEGER,
                status VARCHAR(20) DEFAULT 'запланирован',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tournament_id) REFERENCES tournament (id),
                FOREIGN KEY (participant1_id) REFERENCES participant (id),
                FOREIGN KEY (participant2_id) REFERENCES participant (id),
                FOREIGN KEY (winner_id) REFERENCES participant (id)
            )
        ''')
        
        # Создаем таблицу notification
        cursor.execute('''
            CREATE TABLE notification (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES user (id)
            )
        ''')
        
        # Создаем таблицу match_log
        cursor.execute('''
            CREATE TABLE match_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                action VARCHAR(50) NOT NULL,
                details TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES match (id)
            )
        ''')
        
        # Создаем администратора
        cursor.execute('''
            INSERT INTO user (username, password_hash, role) 
            VALUES ('admin', 'pbkdf2:sha256:260000$8X9vK2xL$...', 'администратор')
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ Новая база данных создана с правильной схемой")
        
        # Проверяем структуру
        print("\n📋 Проверяем структуру таблицы participant:")
        conn = sqlite3.connect('tournament.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(participant)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        conn.close()
        
        print("\n✅ Все готово! Теперь можно запускать приложение.")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    success = simple_fix()
    if success:
        print("\n🚀 Готово! Запускайте приложение командой: python app.py")
    else:
        print("\n💥 Произошла ошибка. Проверьте логи выше.")


