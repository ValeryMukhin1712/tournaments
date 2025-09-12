import sqlite3
import os

db_path = 'instance/tournaments.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    print("Таблицы в базе данных:", tables)
    conn.close()
else:
    print("База данных не найдена!")
