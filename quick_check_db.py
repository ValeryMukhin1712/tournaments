#!/usr/bin/env python3
import sqlite3
import os

print("Проверка структуры базы данных...")

# Проверяем доступные БД
db_paths = ['tournament.db', 'instance/tournament.db', 'instance/tournaments.db']
db_file = None
for path in db_paths:
    if os.path.exists(path):
        db_file = path
        print(f"Найдена БД: {path}")
        break

if not db_file:
    print("БД не найдена")
    exit()

# Подключаемся и проверяем таблицы
conn = sqlite3.connect(db_file)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print(f"Таблицы: {tables}")

# Проверяем таблицу tournament
if 'tournament' in tables:
    cursor.execute("PRAGMA table_info(tournament)")
    columns = cursor.fetchall()
    print("Поля таблицы tournament:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

conn.close()
print("Проверка завершена.")
