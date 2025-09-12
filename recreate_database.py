#!/usr/bin/env python3
"""
Скрипт для пересоздания базы данных с правильной схемой
"""

import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

# Путь к базе данных
DB_PATH = 'tournament.db'

def recreate_database():
    """Пересоздаёт базу данных с правильной схемой"""
    
    # Удаляем старую базу данных если существует
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✅ Удалена старая база данных: {DB_PATH}")
    
    # Создаём новую базу данных
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Создание новой базы данных...")
    
    # Создаём таблицу пользователей
    cursor.execute('''
        CREATE TABLE "user" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash VARCHAR(120) NOT NULL,
            role VARCHAR(20) DEFAULT 'участник',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Таблица 'user' создана")
    
    # Создаём таблицу турниров
    cursor.execute('''
        CREATE TABLE "tournament" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            sport_type VARCHAR(50) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            max_participants INTEGER NOT NULL,
            court_count INTEGER NOT NULL,
            match_duration INTEGER NOT NULL,
            break_duration INTEGER NOT NULL,
            points_win INTEGER NOT NULL,
            points_draw INTEGER NOT NULL,
            points_loss INTEGER NOT NULL,
            points_to_win INTEGER NOT NULL,
            sets_to_win INTEGER NOT NULL DEFAULT 2,
            status VARCHAR(20) DEFAULT 'запланирован',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Таблица 'tournament' создана")
    
    # Создаём таблицу участников
    cursor.execute('''
        CREATE TABLE "participant" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournament (id),
            FOREIGN KEY (user_id) REFERENCES "user" (id),
            UNIQUE(tournament_id, user_id)
        )
    ''')
    print("✅ Таблица 'participant' создана")
    
    # Создаём таблицу матчей с полной схемой сетов
    cursor.execute('''
        CREATE TABLE "match" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            participant1_id INTEGER NOT NULL,
            participant2_id INTEGER NOT NULL,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            winner_id INTEGER,
            match_date DATE,
            match_time TIME,
            court_number INTEGER,
            match_number INTEGER,
            status VARCHAR(20) DEFAULT 'запланирован',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            -- Поля для сетов
            set1_score1 INTEGER,
            set1_score2 INTEGER,
            set2_score1 INTEGER,
            set2_score2 INTEGER,
            set3_score1 INTEGER,
            set3_score2 INTEGER,
            sets_won1 INTEGER DEFAULT 0,
            sets_won2 INTEGER DEFAULT 0,
            FOREIGN KEY (tournament_id) REFERENCES tournament (id),
            FOREIGN KEY (participant1_id) REFERENCES participant (id),
            FOREIGN KEY (participant2_id) REFERENCES participant (id),
            FOREIGN KEY (winner_id) REFERENCES participant (id)
        )
    ''')
    print("✅ Таблица 'match' создана с полной схемой сетов")
    
    # Создаём администратора по умолчанию
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO "user" (username, password_hash, role)
        VALUES (?, ?, ?)
    ''', ('admin', admin_password, 'администратор'))
    print("✅ Администратор создан: admin/admin123")
    
    # Сохраняем изменения
    conn.commit()
    conn.close()
    
    print(f"🎉 База данных успешно пересоздана: {DB_PATH}")
    print("📋 Схема включает все поля для сетов:")
    print("   - set1_score1, set1_score2")
    print("   - set2_score1, set2_score2") 
    print("   - set3_score1, set3_score2")
    print("   - sets_won1, sets_won2")

if __name__ == "__main__":
    recreate_database()
