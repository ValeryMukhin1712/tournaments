#!/usr/bin/env python3
"""
Скрипт для проверки структуры базы данных на сервере
"""
import sqlite3
import os

def check_server_db_structure():
    """Проверяет структуру базы данных на сервере"""

    # Путь к базе данных на сервере tournament-admin@45.135.164.202
    db_path = '/home/tournament-admin/quick-score/instance/tournament.db'

    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return None

    print(f"🔍 Проверяем базу данных на сервере: {db_path}")

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\n📋 Найденные таблицы ({len(tables)}):")
        for table in sorted(tables):
            if not table.startswith('sqlite_'):  # Исключаем системные таблицы
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

        print(f"\n🔍 Проверка структуры таблиц:")

        for table_name in sorted(expected_schema.keys()):
            if table_name not in tables:
                print(f"❌ Таблица '{table_name}' не существует")
                continue

            # Получаем текущие поля таблицы
            cursor.execute(f"PRAGMA table_info({table_name})")
            current_columns = [row[1] for row in cursor.fetchall()]

            expected_columns = expected_schema[table_name]

            # Находим недостающие поля
            missing = [col for col in expected_columns if col not in current_columns]
            # Находим лишние поля
            extra = [col for col in current_columns if col not in expected_columns]

            if missing:
                print(f"❌ Таблица '{table_name}' - недостающие поля: {', '.join(missing)}")
            elif extra:
                print(f"⚠️  Таблица '{table_name}' - есть лишние поля: {', '.join(extra)}")
            else:
                print(f"✅ Таблица '{table_name}' - структура корректна")

            # Показываем все поля таблицы
            if current_columns:
                print(f"   Текущие поля: {', '.join(current_columns)}")

        conn.close()

        print(f"\n✅ Проверка структуры базы данных на сервере завершена!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при проверке базы данных: {e}")
        return False

if __name__ == "__main__":
    check_server_db_structure()
