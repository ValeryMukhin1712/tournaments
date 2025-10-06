#!/usr/bin/env python3
"""
Добавление тестовых игроков в базу данных
"""
import sqlite3
import os

def add_test_players():
    """Добавляет тестовых игроков в базу данных"""
    
    # Путь к базе данных
    db_path = 'instance/tournament.db'
    
    if not os.path.exists(db_path):
        print(f"База данных не найдена: {db_path}")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Тестовые игроки
        test_players = [
            'Иван Петров',
            'Мария Сидорова', 
            'Алексей Козлов',
            'Елена Морозова',
            'Дмитрий Волков',
            'Анна Соколова',
            'Сергей Лебедев',
            'Ольга Новикова'
        ]
        
        added_count = 0
        for player in test_players:
            try:
                cursor.execute('INSERT INTO player (name) VALUES (?)', (player,))
                print(f'Добавлен игрок: {player}')
                added_count += 1
            except sqlite3.IntegrityError:
                print(f'Игрок {player} уже существует')
        
        # Сохраняем изменения
        conn.commit()
        
        print(f'Добавлено новых игроков: {added_count}')
        
        # Показываем всех игроков
        cursor.execute('SELECT id, name, created_at FROM player ORDER BY name')
        players = cursor.fetchall()
        
        print(f'Всего игроков в базе: {len(players)}')
        for player in players:
            print(f'  {player[0]}: {player[1]} (создан: {player[2]})')
        
        return True
        
    except Exception as e:
        print(f"Ошибка при добавлении тестовых игроков: {e}")
        return False
        
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("Добавление тестовых игроков...")
    success = add_test_players()
    
    if success:
        print("Тестовые игроки добавлены успешно!")
    else:
        print("Ошибка при добавлении тестовых игроков!")

