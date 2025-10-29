"""
Миграция для добавления поля telegram в таблицы participant и waiting_list
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.participant import Participant
from models.waiting_list import WaitingList

def migrate():
    """Добавляет поле telegram в таблицы participant и waiting_list"""
    
    with app.app_context():
        try:
            print("Начинаем миграцию...")
            
            # Проверяем текущую структуру таблиц
            inspector = db.inspect(db.engine)
            
            # Проверяем таблицу participant
            participant_columns = [col['name'] for col in inspector.get_columns('participant')]
            print(f"Текущие колонки таблицы participant: {participant_columns}")
            
            # Проверяем таблицу waiting_list
            waiting_list_columns = [col['name'] for col in inspector.get_columns('waiting_list')]
            print(f"Текущие колонки таблицы waiting_list: {waiting_list_columns}")
            
            # Добавляем поле telegram в participant, если его нет
            if 'telegram' not in participant_columns:
                print("Добавляем поле 'telegram' в таблицу participant...")
                with db.engine.begin() as conn:
                    conn.execute(db.text('ALTER TABLE participant ADD COLUMN telegram VARCHAR(100)'))
                print("✅ Поле 'telegram' успешно добавлено в таблицу participant")
            else:
                print("ℹ️  Поле 'telegram' уже существует в таблице participant")
            
            # Добавляем поле telegram в waiting_list, если его нет
            if 'telegram' not in waiting_list_columns:
                print("Добавляем поле 'telegram' в таблицу waiting_list...")
                with db.engine.begin() as conn:
                    conn.execute(db.text('ALTER TABLE waiting_list ADD COLUMN telegram VARCHAR(100)'))
                print("✅ Поле 'telegram' успешно добавлено в таблицу waiting_list")
            else:
                print("ℹ️  Поле 'telegram' уже существует в таблице waiting_list")
            
            # Проверяем результат
            participant_columns_after = [col['name'] for col in inspector.get_columns('participant')]
            waiting_list_columns_after = [col['name'] for col in inspector.get_columns('waiting_list')]
            
            print("\n✅ Миграция завершена успешно!")
            print(f"Колонки таблицы participant после миграции: {participant_columns_after}")
            print(f"Колонки таблицы waiting_list после миграции: {waiting_list_columns_after}")
            
        except Exception as e:
            print(f"❌ Ошибка при миграции: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return False
    
    return True

if __name__ == '__main__':
    print("="*60)
    print("Миграция: Добавление поля telegram")
    print("="*60)
    
    if migrate():
        print("\n✅ Миграция выполнена успешно!")
    else:
        print("\n❌ Миграция не выполнена. Проверьте логи выше.")
        sys.exit(1)

