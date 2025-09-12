#!/usr/bin/env python3
"""
Скрипт для пересоздания базы данных через SQLAlchemy
"""

from app import app, db
from models import create_models

def recreate_database():
    """Пересоздает базу данных через SQLAlchemy"""
    
    with app.app_context():
        try:
            print("🔄 Пересоздаем базу данных через SQLAlchemy...")
            
            # Удаляем все таблицы
            db.drop_all()
            print("✅ Все таблицы удалены")
            
            # Создаем все таблицы заново
            db.create_all()
            print("✅ Все таблицы созданы заново")
            
            # Проверяем, что колонки существуют
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('tournament')]
            
            print(f"Колонки в таблице tournament: {columns}")
            
            if 'start_time' in columns and 'end_time' in columns:
                print("✅ Поля start_time и end_time найдены в базе данных!")
                
                # Создаем администратора по умолчанию
                from models.user import create_user_model
                User = create_user_model(db)
                
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash='pbkdf2:sha256:600000$8d9f8a8b8c8d8e8f$1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
                    role='admin'
                )
                
                db.session.add(admin)
                db.session.commit()
                print("✅ Администратор создан")
                
                return True
            else:
                print("❌ Поля start_time и end_time не найдены!")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка при пересоздании базы данных: {e}")
            return False

if __name__ == "__main__":
    success = recreate_database()
    
    if success:
        print("\n✅ База данных успешно пересоздана!")
    else:
        print("\n❌ Не удалось пересоздать базу данных!")
