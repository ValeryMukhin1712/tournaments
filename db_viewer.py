import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('instance/tournament.db')
cursor = conn.cursor()

# Проверяем таблицу пользователей
print("=== ПОЛЬЗОВАТЕЛИ ===")
cursor.execute("SELECT id, username, password_hash, role FROM user")
users = cursor.fetchall()

for user in users:
    print(f"ID: {user[0]}, Username: {user[1]}, Password: {user[2][:20]}..., Role: {user[3]}")

# Проверяем таблицу турниров
print("\n=== ТУРНИРЫ ===")
cursor.execute("SELECT id, name FROM tournament")
tournaments = cursor.fetchall()

for tournament in tournaments:
    print(f"ID: {tournament[0]}, Name: {tournament[1]}")

# Проверяем таблицу участников
print("\n=== УЧАСТНИКИ ===")
cursor.execute("SELECT id, tournament_id, user_id, name, is_team FROM participant")
participants = cursor.fetchall()

for participant in participants:
    print(f"ID: {participant[0]}, Tournament: {participant[1]}, User: {participant[2]}, Name: {participant[3]}, Is Team: {participant[4]}")

conn.close()
