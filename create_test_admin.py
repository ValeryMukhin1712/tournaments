#!/usr/bin/env python3
"""
Скрипт для создания тестового админа в базе данных
"""
import sqlite3
import os
from datetime import datetime

def create_test_admin():
    """Создает тестового админа myemail@m с токеном 47"""
    
    db_path = 'instance/tournament.db'
    
    if not os.path.exists(db_path):
        print(f"❌ База данных {db_path} не найдена!")
        return False
    
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Создаем тестового админа...")
        
        # Проверяем, существует ли уже админ с таким email
        cursor.execute("SELECT id FROM tournament_admin WHERE email = ?", ('myemail@m',))
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            print("✅ Админ myemail@m уже существует")
            # Обновляем токен
            cursor.execute("UPDATE tournament_admin SET token = ?, is_active = 1 WHERE email = ?", 
                         ('47', 'myemail@m'))
            print("🔄 Токен обновлен на 47")
        else:
            # Создаем нового админа
            cursor.execute("""
                INSERT INTO tournament_admin (name, email, token, created_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, ('Тестовый Админ', 'myemail@m', '47', datetime.utcnow(), 1))
            print("➕ Создан новый админ myemail@m с токеном 47")
        
        # Создаем системного админа
        cursor.execute("SELECT id FROM tournament_admin WHERE email = ?", ('admin@system',))
        system_admin = cursor.fetchone()
        
        if not system_admin:
            cursor.execute("""
                INSERT INTO tournament_admin (name, email, token, created_at, is_active)
                VALUES (?, ?, ?, ?, ?)
            """, ('Системный Админ', 'admin@system', 'admin', datetime.utcnow(), 1))
            print("➕ Создан системный админ admin@system")
        else:
            print("✅ Системный админ уже существует")
        
        # Сохраняем изменения
        conn.commit()
        print("✅ Тестовые админы созданы успешно!")
        
        # Проверяем результат
        cursor.execute("SELECT id, name, email, token, is_active FROM tournament_admin")
        admins = cursor.fetchall()
        print("📋 Список админов:")
        for admin in admins:
            print(f"   ID: {admin[0]}, Имя: {admin[1]}, Email: {admin[2]}, Токен: {admin[3]}, Активен: {admin[4]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании админа: {e}")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("👤 СОЗДАНИЕ ТЕСТОВОГО АДМИНА")
    print("=" * 60)
    
    success = create_test_admin()
    
    if success:
        print("🎉 Тестовые админы созданы успешно!")
    else:
        print("💥 Создание админов завершилось с ошибкой!")
    
    print("=" * 60)