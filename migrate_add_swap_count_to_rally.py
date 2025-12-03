#!/usr/bin/env python3
"""
Миграция для добавления столбца swap_count в таблицу rally
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text, inspect

def migrate_add_swap_count():
    """Добавляет столбец swap_count в таблицу rally"""
    with app.app_context():
        try:
            inspector = db.inspect(db.engine)
            
            # Проверяем, существует ли таблица rally
            tables = inspector.get_table_names()
            if 'rally' not in tables:
                print("❌ Таблица rally не найдена. Сначала создайте таблицу rally.")
                return False
            
            # Проверяем текущие колонки таблицы rally
            rally_columns = [col['name'] for col in inspector.get_columns('rally')]
            print(f"📋 Текущие колонки таблицы rally: {', '.join(rally_columns)}")
            
            # Добавляем поле swap_count, если его нет
            if 'swap_count' not in rally_columns:
                print("➕ Добавляем поле 'swap_count' в таблицу rally...")
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text(
                            'ALTER TABLE rally ADD COLUMN swap_count INTEGER DEFAULT 0'
                        ))
                    print("✅ Поле 'swap_count' успешно добавлено в таблицу rally")
                except Exception as e:
                    print(f"❌ Ошибка при добавлении поля 'swap_count': {e}")
                    import traceback
                    traceback.print_exc()
                    return False
            else:
                print("ℹ️  Поле 'swap_count' уже существует в таблице rally")
            
            # Проверяем результат
            rally_columns_after = [col['name'] for col in inspector.get_columns('rally')]
            print(f"📋 Колонки таблицы rally после миграции: {', '.join(rally_columns_after)}")
            
            # Обновляем существующие записи, устанавливая swap_count = 0 для старых записей
            try:
                with db.engine.begin() as conn:
                    result = conn.execute(text(
                        'UPDATE rally SET swap_count = 0 WHERE swap_count IS NULL'
                    ))
                    print(f"✅ Обновлено {result.rowcount} записей в таблице rally (установлен swap_count = 0)")
            except Exception as e:
                print(f"⚠️  Предупреждение при обновлении записей: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    print("🔄 Запуск миграции для добавления столбца swap_count в таблицу rally...")
    if migrate_add_swap_count():
        print("✅ Миграция завершена успешно")
    else:
        print("❌ Миграция завершилась с ошибкой")
        sys.exit(1)

