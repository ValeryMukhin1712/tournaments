#!/usr/bin/env python3
"""
Скрипт для создания правильной базы данных на основе реальных моделей проекта
"""

import os
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

# Путь к базе данных
DB_PATH = 'instance/tournament.db'

def create_correct_database():
    """Создаёт правильную базу данных на основе моделей проекта"""
    
    # Удаляем старую базу данных если существует
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✅ Удалена старая база данных: {DB_PATH}")
    
    # Создаём новую базу данных
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("🔄 Создание правильной базы данных на основе моделей...")
    
    # 1. Таблица пользователей (user)
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
    
    # 2. Таблица турниров (tournament)
    cursor.execute('''
        CREATE TABLE "tournament" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            sport_type VARCHAR(50) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            max_participants INTEGER DEFAULT 32,
            court_count INTEGER DEFAULT 3,
            match_duration INTEGER DEFAULT 60,
            break_duration INTEGER DEFAULT 15,
            points_win INTEGER DEFAULT 3,
            points_draw INTEGER DEFAULT 1,
            points_loss INTEGER DEFAULT 0,
            points_to_win INTEGER DEFAULT 21,
            sets_to_win INTEGER DEFAULT 2,
            status VARCHAR(20) DEFAULT 'регистрация',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("✅ Таблица 'tournament' создана")
    
    # 3. Таблица участников (participant) - ВАЖНО: есть поле name!
    cursor.execute('''
        CREATE TABLE "participant" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER,
            name VARCHAR(100) NOT NULL,
            is_team BOOLEAN DEFAULT 0,
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tournament_id) REFERENCES tournament (id),
            FOREIGN KEY (user_id) REFERENCES "user" (id),
            UNIQUE(tournament_id, user_id)
        )
    ''')
    print("✅ Таблица 'participant' создана с полем 'name'")
    
    # 4. Таблица матчей (match) с полной схемой сетов
    cursor.execute('''
        CREATE TABLE "match" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            participant1_id INTEGER NOT NULL,
            participant2_id INTEGER NOT NULL,
            score1 INTEGER,
            score2 INTEGER,
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
    
    print(f"🎉 Правильная база данных создана: {DB_PATH}")
    print("📋 Структура соответствует моделям проекта:")
    print("   - user: id, username, password_hash, role, created_at")
    print("   - tournament: id, name, sport_type, start_date, end_date, max_participants, court_count, match_duration, break_duration, points_win, points_draw, points_loss, points_to_win, sets_to_win, status, created_at")
    print("   - participant: id, tournament_id, user_id, name, is_team, registered_at")
    print("   - match: id, tournament_id, participant1_id, participant2_id, score1, score2, winner_id, match_date, match_time, court_number, match_number, status, created_at, updated_at, set1_score1, set1_score2, set2_score1, set2_score2, set3_score1, set3_score2, sets_won1, sets_won2")

if __name__ == "__main__":
    create_correct_database()
