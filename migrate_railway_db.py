#!/usr/bin/env python3
"""
Скрипт для миграции базы данных на Railway
Добавляет недостающие колонки в таблицы
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

def get_database_url():
    """Получает URL базы данных из переменных окружения"""
    # Проверяем переменные окружения Railway
    if 'DATABASE_URL' in os.environ:
        return os.environ['DATABASE_URL']
    
    # Если нет DATABASE_URL, используем SQLite
    return 'sqlite:///instance/tournament.db'

def add_missing_columns(engine):
    """Добавляет недостающие колонки в таблицы"""
    with engine.connect() as conn:
        # Проверяем существование таблиц
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"Найденные таблицы: {tables}")
        
        # Добавляем колонку points в таблицу participant
        if 'participant' in tables:
            try:
                # Проверяем, существует ли колонка points
                columns = inspector.get_columns('participant')
                column_names = [col['name'] for col in columns]
                
                if 'points' not in column_names:
                    print("Добавляем колонку 'points' в таблицу 'participant'...")
                    conn.execute(text("ALTER TABLE participant ADD COLUMN points INTEGER DEFAULT 0"))
                    conn.commit()
                    print("Колонка 'points' успешно добавлена")
                else:
                    print("Колонка 'points' уже существует в таблице 'participant'")
                    
            except Exception as e:
                print(f"Ошибка при добавлении колонки 'points': {e}")
        
        # Добавляем колонки для сетов в таблицу match
        if 'match' in tables:
            try:
                columns = inspector.get_columns('match')
                column_names = [col['name'] for col in columns]
                
                # Добавляем колонки для сетов
                set_columns = [
                    'set1_score1', 'set1_score2',
                    'set2_score1', 'set2_score2', 
                    'set3_score1', 'set3_score2'
                ]
                
                for col in set_columns:
                    if col not in column_names:
                        print(f"Добавляем колонку '{col}' в таблицу 'match'...")
                        conn.execute(text(f"ALTER TABLE match ADD COLUMN {col} INTEGER DEFAULT 0"))
                        conn.commit()
                        print(f"Колонка '{col}' успешно добавлена")
                    else:
                        print(f"Колонка '{col}' уже существует в таблице 'match'")
                        
            except Exception as e:
                print(f"Ошибка при добавлении колонок сетов: {e}")

def main():
    """Основная функция"""
    try:
        # Получаем URL базы данных
        database_url = get_database_url()
        print(f"Подключаемся к базе данных: {database_url}")
        
        # Создаем подключение
        engine = create_engine(database_url)
        
        # Тестируем подключение
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Подключение к базе данных успешно")
        
        # Добавляем недостающие колонки
        add_missing_columns(engine)
        
        print("Миграция базы данных завершена успешно!")
        
    except Exception as e:
        print(f"Ошибка при миграции базы данных: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
