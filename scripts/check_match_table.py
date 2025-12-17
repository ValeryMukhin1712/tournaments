"""
Проверка структуры таблицы match
"""
import sqlite3
from pathlib import Path

# Пытаемся работать с instance/tournament.db, если он существует,
# иначе используем tournament.db в корне.
INSTANCE_DB = Path("instance") / "tournament.db"
DB = INSTANCE_DB if INSTANCE_DB.exists() else Path("tournament.db")

def main():
    if not DB.exists():
        print(f"База данных не найдена: {DB}")
        return
    
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    
    print("=== Структура таблицы match ===\n")
    
    # Получаем информацию о колонках
    cur.execute("PRAGMA table_info('match')")
    columns = cur.fetchall()
    
    print(f"{'Имя колонки':<25} {'Тип':<15} {'NOT NULL':<10} {'Default':<15} {'PK':<5}")
    print("-" * 75)
    
    for col in columns:
        cid, name, col_type, not_null, default_val, pk = col
        not_null_str = "YES" if not_null else "NO"
        pk_str = "YES" if pk else "NO"
        default_str = str(default_val) if default_val else ""
        print(f"{name:<25} {col_type:<15} {not_null_str:<10} {default_str:<15} {pk_str:<5}")
    
    print("\n=== Проверка ключевых полей для свободных матчей ===\n")
    
    # Проверяем конкретные поля
    key_fields = ['tournament_id', 'player1_id', 'player2_id', 'player1_name', 'player2_name', 'winner_player_id']
    
    for field in key_fields:
        found = False
        nullable = False
        for col in columns:
            if col[1] == field:
                found = True
                nullable = col[3] == 0  # 0 = nullable, 1 = NOT NULL
                break
        
        if found:
            status = "✅ NULLABLE" if nullable else "❌ NOT NULL"
            print(f"{field:<25} {status}")
        else:
            print(f"{field:<25} ❌ НЕ НАЙДЕНО")
    
    # Проверяем foreign keys
    print("\n=== Foreign Keys ===\n")
    cur.execute("PRAGMA foreign_key_list('match')")
    fks = cur.fetchall()
    if fks:
        for fk in fks:
            print(f"From: {fk[3]} -> To: {fk[2]}.{fk[4]}")
    else:
        print("Foreign keys не найдены (возможно, отключены)")
    
    conn.close()
    print("\n=== Проверка завершена ===")

if __name__ == "__main__":
    main()
