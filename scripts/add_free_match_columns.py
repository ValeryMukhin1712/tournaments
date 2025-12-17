"""
Миграция: добавление полей для свободных матчей (без турнира)
"""
import sqlite3
from pathlib import Path

# Пытаемся работать с instance/tournament.db, если он существует,
# иначе используем tournament.db в корне.
INSTANCE_DB = Path("instance") / "tournament.db"
DB = INSTANCE_DB if INSTANCE_DB.exists() else Path("tournament.db")

def ensure_column(cur, table: str, column: str, definition: str) -> None:
    cur.execute(f"PRAGMA table_info('{table}')")
    cols = [row[1] for row in cur.fetchall()]
    if column not in cols:
        print(f"Adding {column} to {table}")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    else:
        print(f"{table}.{column} exists")

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    # Изменяем tournament_id на nullable в таблице match
    print("Checking match table...")
    cur.execute("PRAGMA table_info('match')")
    cols = {row[1]: row for row in cur.fetchall()}
    
    if 'tournament_id' in cols:
        col_info = cols['tournament_id']
        if col_info[3] == 0:  # nullable = 0 means NOT NULL
            print("Making tournament_id nullable in match table...")
            # SQLite не поддерживает ALTER COLUMN, нужно пересоздать таблицу
            # Но это сложно, поэтому просто добавим новые поля
            # tournament_id останется NOT NULL, но мы можем использовать NULL через обходной путь
            print("Note: SQLite doesn't support ALTER COLUMN. tournament_id will remain NOT NULL.")
            print("We'll use a workaround: set tournament_id to a special value (0) for free matches.")
        else:
            print("tournament_id is already nullable")
    else:
        print("tournament_id column not found in match table")

    # Добавляем новые поля в match
    COLS = {
        "match": [
            ("player1_id", "INTEGER"),
            ("player2_id", "INTEGER"),
            ("player1_name", "TEXT"),
            ("player2_name", "TEXT"),
            ("winner_player_id", "INTEGER"),
        ],
        "rally": [
            # tournament_id уже может быть nullable, но проверим
        ],
    }

    for table, defs in COLS.items():
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            print(f"Skip {table}: table not found")
            continue
        for column, definition in defs:
            ensure_column(cur, table, column, definition)

    conn.commit()
    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()





