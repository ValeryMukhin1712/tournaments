"""
Исправление: делаем tournament_id nullable в таблице match
SQLite не поддерживает ALTER COLUMN напрямую, поэтому нужно пересоздать таблицу
"""
import sqlite3
from pathlib import Path
import shutil
from datetime import datetime

# Пытаемся работать с instance/tournament.db, если он существует,
# иначе используем tournament.db в корне.
INSTANCE_DB = Path("instance") / "tournament.db"
DB = INSTANCE_DB if INSTANCE_DB.exists() else Path("tournament.db")

def main():
    if not DB.exists():
        print(f"База данных не найдена: {DB}")
        return
    
    # Создаем резервную копию
    backup_path = DB.parent / f"{DB.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    print(f"Создаем резервную копию: {backup_path}")
    shutil.copy2(DB, backup_path)
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    # Отключаем foreign keys временно
    cur.execute("PRAGMA foreign_keys=OFF")
    
    try:
        # Получаем структуру существующей таблицы
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='match'")
        create_sql = cur.fetchone()[0]
        print(f"Текущая структура:\n{create_sql}\n")
        
        # Создаем временную таблицу с правильной структурой
        # Заменяем tournament_id INTEGER NOT NULL на tournament_id INTEGER
        new_sql = create_sql.replace(
            "tournament_id INTEGER NOT NULL",
            "tournament_id INTEGER"
        ).replace(
            "tournament_id INTEGER,",
            "tournament_id INTEGER,"
        )
        
        # Если не нашлось NOT NULL, попробуем другой вариант
        if "tournament_id INTEGER NOT NULL" not in create_sql:
            # Ищем точное место
            import re
            new_sql = re.sub(
                r'tournament_id\s+INTEGER\s+NOT\s+NULL',
                'tournament_id INTEGER',
                create_sql
            )
        
        # Создаем временную таблицу с правильным именем
        temp_table_sql = new_sql.replace("CREATE TABLE \"match\"", "CREATE TABLE \"match_new\"").replace("CREATE TABLE match", "CREATE TABLE match_new")
        print(f"Создаем временную таблицу match_new...")
        cur.execute(temp_table_sql)
        
        # Копируем данные
        print("Копируем данные из match в match_new...")
        cur.execute("""
            INSERT INTO match_new 
            SELECT * FROM match
        """)
        
        # Удаляем старую таблицу
        print("Удаляем старую таблицу match...")
        cur.execute("DROP TABLE match")
        
        # Переименовываем новую таблицу
        print("Переименовываем match_new в match...")
        cur.execute("ALTER TABLE match_new RENAME TO match")
        
        # Восстанавливаем индексы и foreign keys
        print("Восстанавливаем foreign keys...")
        cur.execute("PRAGMA foreign_keys=ON")
        
        conn.commit()
        print("\n✅ Таблица match успешно обновлена!")
        print(f"✅ Резервная копия сохранена: {backup_path}")
        
        # Проверяем результат
        cur.execute("PRAGMA table_info('match')")
        columns = cur.fetchall()
        for col in columns:
            if col[1] == 'tournament_id':
                nullable = col[3] == 0
                print(f"\nПроверка: tournament_id nullable = {nullable}")
                if nullable:
                    print("✅ tournament_id теперь nullable!")
                else:
                    print("❌ tournament_id все еще NOT NULL!")
                break
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Ошибка: {e}")
        print(f"Восстанавливаем из резервной копии...")
        shutil.copy2(backup_path, DB)
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()

