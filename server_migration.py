#!/usr/bin/env python3
"""
Скрипт для миграции базы данных на сервере
Применяет все необходимые миграции для синхронизации схемы БД
"""
import sqlite3
import os
from datetime import datetime

def run_migrations():
    """Выполняет все необходимые миграции базы данных"""

    # Путь к базе данных на сервере (адаптируется под разные серверы)
    # Для сервера tournament-admin@45.135.164.202
    db_path = '/home/tournament-admin/quick-score/instance/tournament.db'

    # Для сервера deploy@89.19.44.212 (закомментировано)
    # db_path = '/home/deploy/quick-score/instance/tournament.db'

    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False

    print(f"🔄 Начинаем миграцию базы данных: {db_path}")

    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Миграция 1: Добавляем поля start_time и end_time в таблицу tournament
        print("📋 Миграция 1: Добавление полей времени в таблицу tournament")
        migrate_tournament_time_fields(cursor)

        # Миграция 2: Добавляем поле swap_count в таблицу rally
        print("📋 Миграция 2: Добавление поля swap_count в таблицу rally")
        migrate_rally_swap_count(cursor)

        # Миграция 3: Добавляем дополнительные поля в таблицу match
        print("📋 Миграция 3: Добавление дополнительных полей в таблицу match")
        migrate_match_additional_fields(cursor)

        # Миграция 4: Создаем таблицу waiting_list если её нет
        print("📋 Миграция 4: Создание таблицы waiting_list")
        migrate_waiting_list_table(cursor)

        # Сохраняем изменения
        conn.commit()
        conn.close()

        print("✅ Все миграции выполнены успешно!")
        return True

    except Exception as e:
        print(f"❌ Ошибка при выполнении миграций: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def migrate_tournament_time_fields(cursor):
    """Добавляет поля start_time и end_time в таблицу tournament"""
    try:
        # Проверяем, существуют ли уже колонки
        cursor.execute("PRAGMA table_info(tournament)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'start_time' not in columns:
            print("  ➕ Добавляем поле start_time")
            cursor.execute("ALTER TABLE tournament ADD COLUMN start_time TIME DEFAULT '09:00'")
        else:
            print("  ✅ Поле start_time уже существует")

        if 'end_time' not in columns:
            print("  ➕ Добавляем поле end_time")
            cursor.execute("ALTER TABLE tournament ADD COLUMN end_time TIME DEFAULT '17:00'")
        else:
            print("  ✅ Поле end_time уже существует")

    except Exception as e:
        print(f"  ❌ Ошибка при миграции полей времени: {e}")

def migrate_rally_swap_count(cursor):
    """Добавляет поле swap_count в таблицу rally"""
    try:
        # Проверяем, существует ли таблица rally
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rally'")
        if not cursor.fetchone():
            print("  ⚠️  Таблица rally не существует, пропускаем миграцию")
            return

        # Проверяем, существует ли поле swap_count
        cursor.execute("PRAGMA table_info(rally)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'swap_count' not in columns:
            print("  ➕ Добавляем поле swap_count")
            cursor.execute("ALTER TABLE rally ADD COLUMN swap_count INTEGER DEFAULT 0")
            # Обновляем существующие записи
            cursor.execute("UPDATE rally SET swap_count = 0 WHERE swap_count IS NULL")
        else:
            print("  ✅ Поле swap_count уже существует")

    except Exception as e:
        print(f"  ❌ Ошибка при миграции swap_count: {e}")

def migrate_match_additional_fields(cursor):
    """Добавляет дополнительные поля в таблицу match"""
    try:
        # Проверяем, существует ли таблица match
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match'")
        if not cursor.fetchone():
            print("  ⚠️  Таблица match не существует, пропускаем миграцию")
            return

        cursor.execute("PRAGMA table_info(match)")
        columns = [column[1] for column in cursor.fetchall()]

        # Список полей для добавления
        fields_to_add = {
            'actual_start_time': 'DATETIME',
            'actual_end_time': 'DATETIME',
            'set1_score1': 'INTEGER',
            'set1_score2': 'INTEGER',
            'set2_score1': 'INTEGER',
            'set2_score2': 'INTEGER',
            'set3_score1': 'INTEGER',
            'set3_score2': 'INTEGER',
            'winner_player_id': 'INTEGER',
            'player1_id': 'INTEGER',
            'player2_id': 'INTEGER',
            'player1_name': 'VARCHAR(100)',
            'player2_name': 'VARCHAR(100)',
            'is_removed': 'BOOLEAN DEFAULT 0',
            'deleted_at': 'DATETIME',
            'deleted_by': 'VARCHAR(100)'
        }

        for field_name, field_type in fields_to_add.items():
            if field_name not in columns:
                print(f"  ➕ Добавляем поле {field_name}")
                cursor.execute(f"ALTER TABLE match ADD COLUMN {field_name} {field_type}")
            else:
                print(f"  ✅ Поле {field_name} уже существует")

    except Exception as e:
        print(f"  ❌ Ошибка при миграции полей match: {e}")

def migrate_waiting_list_table(cursor):
    """Создает таблицу waiting_list если её нет"""
    try:
        # Проверяем, существует ли таблица waiting_list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='waiting_list'")
        if cursor.fetchone():
            print("  ✅ Таблица waiting_list уже существует")
            return

        print("  ➕ Создаем таблицу waiting_list")

        # Создаем таблицу waiting_list
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

        # Создаем индексы
        cursor.execute("CREATE INDEX idx_waiting_list_tournament_id ON waiting_list (tournament_id)")
        cursor.execute("CREATE INDEX idx_waiting_list_status ON waiting_list (status)")

        print("  ✅ Таблица waiting_list создана")

    except Exception as e:
        print(f"  ❌ Ошибка при создании таблицы waiting_list: {e}")

if __name__ == "__main__":
    print("🚀 Запуск миграции базы данных на сервере...")
    success = run_migrations()

    if success:
        print("\n✅ Миграция завершена успешно!")
        print("📝 Рекомендуется:")
        print("   1. Остановить приложение: sudo systemctl stop tournaments")
        print("   2. Перезапустить приложение: sudo systemctl start tournaments")
        print("   3. Проверить логи: sudo journalctl -u tournaments -n 20")
    else:
        print("\n❌ Миграция завершилась с ошибками!")
        print("📝 Проверьте логи выше для диагностики проблем.")
