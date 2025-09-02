#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import os

# Путь к базе данных
db_path = os.path.join('instance', 'tournament.db')

if not os.path.exists(db_path):
    print("База данных не найдена!")
    exit(1)

# Подключение к базе данных
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== ПОЛЬЗОВАТЕЛИ ===")
cursor.execute("SELECT id, username, role FROM user")
users = cursor.fetchall()
for user in users:
    print(f"ID: {user[0]}, Username: {user[1]}, Role: {user[2]}")

print("\n=== УЧАСТНИКИ ТУРНИРОВ ===")
cursor.execute("SELECT id, tournament_id, user_id, name, is_team FROM participant")
participants = cursor.fetchall()
for participant in participants:
    print(f"ID: {participant[0]}, Tournament: {participant[1]}, User ID: {participant[2]}, Name: {participant[3]}, Is Team: {participant[4]}")

print("\n=== ТУРНИРЫ ===")
cursor.execute("SELECT id, name FROM tournament")
tournaments = cursor.fetchall()
for tournament in tournaments:
    print(f"ID: {tournament[0]}, Name: {tournament[1]}")

conn.close()
