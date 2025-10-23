#!/usr/bin/env python3
"""
Скрипт инициализации базы данных для Quick Score Tournaments

Использование:
    python init_db.py

Что делает:
    - Создает все необходимые таблицы
    - Создает администратора по умолчанию (admin/adm555)
    - Инициализирует настройки по умолчанию
"""

import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, init_db, logger

if __name__ == '__main__':
    print("=" * 60)
    print("Инициализация базы данных Quick Score Tournaments")
    print("=" * 60)
    
    try:
        init_db()
        print("\n✓ База данных успешно инициализирована!")
        print("\nДанные для входа:")
        print("  Логин: admin")
        print("  Пароль: adm555")
        print("\n⚠️  ВАЖНО: Измените пароль администратора после первого входа!")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        print(f"\n✗ Ошибка: {e}")
        sys.exit(1)

