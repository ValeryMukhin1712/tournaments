#!/usr/bin/env python3
"""
Миграция для добавления уникального ограничения на поле token (пароли)
"""
import sqlite3
import os
import sys
from datetime import datetime

def migrate_database():
    """Добавляет уникальное ограничение на поле token (пароли)"""
    
    # Путь к базе данных
    db_paths = [
        'instance/tournament.db',
        'tournament.db'
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ База данных не найдена!")
        return False
    
    print(f"🔍 Найдена база данных: {db_path}")
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем существующую структуру таблицы tokens
        cursor.execute("PRAGMA table_info(tokens)")
        columns = cursor.fetchall()
        print(f"📋 Текущие колонки таблицы tokens: {[col[1] for col in columns]}")
        
        # Проверяем, есть ли уже уникальное ограничение
        cursor.execute("PRAGMA index_list(tokens)")
        indexes = cursor.fetchall()
        
        has_unique_token = False
        for index in indexes:
            cursor.execute(f"PRAGMA index_info({index[1]})")
            index_info = cursor.fetchall()
            if any(info[2] == 'token' for info in index_info) and index[2] == 1:  # unique index
                has_unique_token = True
                break
        
        if has_unique_token:
            print("✅ Уникальное ограничение на поле token уже существует")
            return True
        
        # Проверяем наличие дублирующихся токенов
        cursor.execute("SELECT token, COUNT(*) FROM tokens GROUP BY token HAVING COUNT(*) > 1")
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"⚠️  Найдены дублирующиеся токены: {duplicates}")
            print("🔧 Обновляем дублирующиеся токены...")
            
            import random
            for token_value, count in duplicates:
                # Получаем все записи с этим токеном
                cursor.execute("SELECT id FROM tokens WHERE token = ? ORDER BY created_at", (token_value,))
                token_ids = cursor.fetchall()
                
                # Оставляем первый токен, остальные обновляем
                for i, (token_id,) in enumerate(token_ids[1:], 1):
                    # Генерируем новый уникальный токен
                    while True:
                        new_token = random.randint(100000, 999999)
                        cursor.execute("SELECT COUNT(*) FROM tokens WHERE token = ?", (new_token,))
                        if cursor.fetchone()[0] == 0:
                            break
                    
                    cursor.execute("UPDATE tokens SET token = ? WHERE id = ?", (new_token, token_id))
                    print(f"   Токен ID {token_id}: {token_value} → {new_token}")
        
        # Создаем уникальный индекс
        print("🔧 Создаем уникальный индекс на поле token...")
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_tokens_token_unique ON tokens(token)")
        
        # Сохраняем изменения
        conn.commit()
        print("✅ Миграция успешно выполнена!")
        
        # Проверяем результат
        cursor.execute("SELECT COUNT(DISTINCT token) as unique_tokens, COUNT(*) as total_tokens FROM tokens")
        unique_count, total_count = cursor.fetchone()
        print(f"📊 Статистика: {unique_count} уникальных токенов из {total_count} общих")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при выполнении миграции: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Запуск миграции для добавления уникального ограничения на токены...")
    print(f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = migrate_database()
    
    if success:
        print("🎉 Миграция завершена успешно!")
        sys.exit(0)
    else:
        print("💥 Миграция завершилась с ошибкой!")
        sys.exit(1)
