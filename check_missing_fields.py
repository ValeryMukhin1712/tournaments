#!/usr/bin/env python3
"""
Проверка недостающих полей в базе данных
"""
import sqlite3
import os

def check_missing_fields():
    """Проверяет и выводит недостающие поля в базе данных"""
    
    # Проверяем существующие файлы базы данных
    db_files = ['tournament.db', 'instance/tournaments.db']
    db_file = None
    
    for file_path in db_files:
        if os.path.exists(file_path):
            db_file = file_path
            break
    
    if not db_file:
        print("❌ База данных не найдена!")
        return
    
    print(f"🔍 Проверяем базу данных: {db_file}")
    
    # Подключаемся к базе данных
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Определяем ожидаемые поля для каждой таблицы
    expected_fields = {
        'user': ['id', 'username', 'password_hash', 'role', 'created_at'],
        'tournament': ['id', 'name', 'description', 'start_date', 'end_date', 'max_participants', 
                      'court_count', 'match_duration', 'break_duration', 'sets_to_win', 
                      'points_to_win', 'points_win', 'points_draw', 'points_loss', 
                      'start_time', 'end_time', 'created_at', 'created_by'],
        'participant': ['id', 'tournament_id', 'user_id', 'name', 'is_team', 'points', 'registered_at'],
        'match': ['id', 'tournament_id', 'participant1_id', 'participant2_id', 'match_date', 
                 'match_time', 'court_number', 'match_number', 'score1', 'score2', 'score', 
                 'sets_won_1', 'sets_won_2', 'winner_id', 'status', 'created_at', 'updated_at'],
        'notification': ['id', 'user_id', 'message', 'is_read', 'created_at'],
        'match_log': ['id', 'match_id', 'action', 'details', 'created_at']
    }
    
    missing_fields = {}
    
    # Проверяем каждую таблицу
    for table_name, expected_columns in expected_fields.items():
        try:
            # Получаем структуру таблицы
            cursor.execute(f"PRAGMA table_info({table_name})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            # Находим недостающие поля
            missing = [col for col in expected_columns if col not in existing_columns]
            
            if missing:
                missing_fields[table_name] = missing
                print(f"❌ Таблица '{table_name}' - недостающие поля: {', '.join(missing)}")
            else:
                print(f"✅ Таблица '{table_name}' - все поля на месте")
                
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                print(f"❌ Таблица '{table_name}' не существует")
                missing_fields[table_name] = expected_columns
            else:
                print(f"❌ Ошибка при проверке таблицы '{table_name}': {e}")
    
    conn.close()
    
    # Выводим итоговый отчет
    if missing_fields:
        print(f"\n📋 ИТОГОВЫЙ ОТЧЕТ:")
        print(f"🔴 Найдено {len(missing_fields)} таблиц с недостающими полями:")
        for table, fields in missing_fields.items():
            print(f"   - {table}: {', '.join(fields)}")
    else:
        print(f"\n✅ ВСЕ ПОЛЯ НА МЕСТЕ! База данных соответствует моделям.")
    
    return missing_fields

if __name__ == "__main__":
    check_missing_fields()


