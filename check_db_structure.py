#!/usr/bin/env python3
"""
Проверка структуры базы данных и сравнение с ожидаемой схемой
"""
import sqlite3
import os
from pathlib import Path

def check_database_structure():
    """Проверяет структуру базы данных"""

    # Определяем пути к базам данных
    db_paths = [
        'tournament.db',
        'instance/tournament.db',
        'instance/tournaments.db'
    ]

    db_file = None
    for path in db_paths:
        if os.path.exists(path):
            db_file = path
            print(f"✅ Найдена база данных: {path}")
            break

    if not db_file:
        print("❌ База данных не найдена!")
        return None

    # Подключаемся к базе данных
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Получаем список всех таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\n📋 Найденные таблицы ({len(tables)}):")
    for table in sorted(tables):
        print(f"  - {table}")

    # Определяем ожидаемые поля для каждой таблицы
    expected_schema = {
        'user': ['id', 'username', 'password_hash', 'role', 'created_at'],
        'tournament': ['id', 'name', 'description', 'start_date', 'end_date', 'max_participants',
                      'court_count', 'match_duration', 'break_duration', 'sets_to_win',
                      'points_to_win', 'points_win', 'points_draw', 'points_loss',
                      'start_time', 'end_time', 'created_at', 'created_by'],
        'participant': ['id', 'tournament_id', 'user_id', 'name', 'is_team', 'points', 'registered_at'],
        'match': ['id', 'tournament_id', 'participant1_id', 'participant2_id', 'match_date',
                 'match_time', 'court_number', 'match_number', 'score1', 'score2', 'score',
                 'sets_won_1', 'sets_won_2', 'winner_id', 'status', 'created_at', 'updated_at'],
        'rally': ['id', 'match_id', 'player1_score', 'player2_score', 'server', 'winner', 'rally_number',
                 'start_time', 'end_time', 'duration', 'created_at', 'swap_count'],
        'match_log': ['id', 'match_id', 'action', 'details', 'created_at'],
        'notification': ['id', 'user_id', 'message', 'is_read', 'created_at'],
        'waiting_list': ['id', 'tournament_id', 'name', 'skill_level', 'created_at', 'status']
    }

    missing_fields = {}
    extra_fields = {}

    print(f"\n🔍 Проверка структуры таблиц:")

    for table_name, expected_columns in expected_schema.items():
        if table_name not in tables:
            print(f"❌ Таблица '{table_name}' не существует")
            missing_fields[table_name] = expected_columns
            continue

        # Получаем текущие поля таблицы
        cursor.execute(f"PRAGMA table_info({table_name})")
        current_columns = [row[1] for row in cursor.fetchall()]

        # Находим недостающие поля
        missing = [col for col in expected_columns if col not in current_columns]
        if missing:
            missing_fields[table_name] = missing
            print(f"❌ Таблица '{table_name}' - недостающие поля: {', '.join(missing)}")
        else:
            print(f"✅ Таблица '{table_name}' - все поля на месте")

        # Находим лишние поля
        extra = [col for col in current_columns if col not in expected_columns]
        if extra:
            extra_fields[table_name] = extra
            print(f"⚠️  Таблица '{table_name}' - лишние поля: {', '.join(extra)}")

    conn.close()

    # Вывод итогового отчета
    print(f"\n📊 ИТОГОВЫЙ ОТЧЕТ:")

    if missing_fields:
        print(f"🔴 Найдено {len(missing_fields)} таблиц с недостающими полями:")
        for table, fields in missing_fields.items():
            print(f"   - {table}: {', '.join(fields)}")
    else:
        print(f"✅ Все ожидаемые поля присутствуют")

    if extra_fields:
        print(f"⚠️  Найдено {len(extra_fields)} таблиц с лишними полями:")
        for table, fields in extra_fields.items():
            print(f"   - {table}: {', '.join(fields)}")

    return {
        'db_file': db_file,
        'missing_fields': missing_fields,
        'extra_fields': extra_fields,
        'tables': tables
    }

if __name__ == "__main__":
    result = check_database_structure()
