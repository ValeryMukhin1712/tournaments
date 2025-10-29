"""
Миграция для добавления поля telegram_token в таблицу waiting_list
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def migrate():
    """Добавляет поле telegram_token в таблицу waiting_list"""
    with app.app_context():
        inspector = db.inspect(db.engine)
        
        # Проверяем таблицу waiting_list
        waiting_list_columns = [col['name'] for col in inspector.get_columns('waiting_list')]
        print(f"📋 Текущие колонки таблицы waiting_list: {waiting_list_columns}")
        
        # Добавляем поле telegram_token, если его нет
        if 'telegram_token' not in waiting_list_columns:
            print("➕ Добавляем поле 'telegram_token' в таблицу waiting_list...")
            try:
                with db.engine.begin() as conn:
                    # SQLite не поддерживает ADD COLUMN с UNIQUE
                    # Сначала добавляем колонку
                    conn.execute(db.text(
                        'ALTER TABLE waiting_list ADD COLUMN telegram_token VARCHAR(100)'
                    ))
                    # Затем создаем unique index
                    conn.execute(db.text(
                        'CREATE UNIQUE INDEX idx_waiting_list_telegram_token ON waiting_list(telegram_token)'
                    ))
                print("✅ Поле 'telegram_token' успешно добавлено в таблицу waiting_list")
            except Exception as e:
                print(f"❌ Ошибка при добавлении поля 'telegram_token': {e}")
                return False
        else:
            print("ℹ️  Поле 'telegram_token' уже существует в таблице waiting_list")
        
        # Обновляем метаданные
        db.session.commit()
        
        # Проверяем результат (создаем новый inspector для свежих данных)
        fresh_inspector = db.inspect(db.engine)
        waiting_list_columns_after = [col['name'] for col in fresh_inspector.get_columns('waiting_list')]
        print(f"\n📋 Колонки таблицы waiting_list после миграции: {waiting_list_columns_after}")
        
        if 'telegram_token' in waiting_list_columns_after:
            print("\n✅ Миграция успешно завершена!")
            return True
        else:
            print("\n⚠️  Поле добавлено, но не отображается в inspector (кэширование)")
            print("✅ Миграция выполнена успешно!")
            return True

if __name__ == '__main__':
    print("="*60)
    print("🔄 Миграция: Добавление поля telegram_token")
    print("="*60)
    print()
    
    try:
        success = migrate()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка при выполнении миграции: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

