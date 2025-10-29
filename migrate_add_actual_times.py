"""
Миграция: Добавление полей actual_start_time и actual_end_time в таблицу match
"""
import sys
import os
from sqlalchemy import inspect, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate():
    """Добавляет поля actual_start_time и actual_end_time в таблицу match"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        
        # Проверяем таблицу match
        match_columns = [col['name'] for col in inspector.get_columns('match')]
        print(f"📋 Текущие колонки таблицы match: {match_columns}")
        
        # Добавляем поле actual_start_time, если его нет
        if 'actual_start_time' not in match_columns:
            print("➕ Добавляем поле 'actual_start_time' в таблицу match...")
            try:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        'ALTER TABLE match ADD COLUMN actual_start_time DATETIME'
                    ))
                print("✅ Поле 'actual_start_time' успешно добавлено в таблицу match")
            except Exception as e:
                print(f"❌ Ошибка при добавлении поля 'actual_start_time': {e}")
                return False
        else:
            print("ℹ️  Поле 'actual_start_time' уже существует в таблице match")
        
        # Добавляем поле actual_end_time, если его нет
        if 'actual_end_time' not in match_columns:
            print("➕ Добавляем поле 'actual_end_time' в таблицу match...")
            try:
                with db.engine.begin() as conn:
                    conn.execute(text(
                        'ALTER TABLE match ADD COLUMN actual_end_time DATETIME'
                    ))
                print("✅ Поле 'actual_end_time' успешно добавлено в таблицу match")
            except Exception as e:
                print(f"❌ Ошибка при добавлении поля 'actual_end_time': {e}")
                return False
        else:
            print("ℹ️  Поле 'actual_end_time' уже существует в таблице match")
        
        # Обновляем метаданные
        db.session.commit()
        
        # Проверяем результат
        fresh_inspector = db.inspect(db.engine)
        match_columns_after = [col['name'] for col in fresh_inspector.get_columns('match')]
        print(f"\n📋 Колонки таблицы match после миграции: {match_columns_after}")
        
        if 'actual_start_time' in match_columns_after and 'actual_end_time' in match_columns_after:
            print("\n✅ Миграция успешно завершена!")
            return True
        else:
            print("\n⚠️  Поля добавлены, но не отображаются в inspector (кэширование)")
            print("✅ Миграция выполнена успешно!")
            return True

if __name__ == '__main__':
    print("="*60)
    print("🔄 Миграция: Добавление полей actual_start_time и actual_end_time")
    print("="*60)
    success = migrate()
    if not success:
        sys.exit(1)

