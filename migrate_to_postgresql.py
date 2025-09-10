#!/usr/bin/env python3
"""
Скрипт миграции данных из SQLite в PostgreSQL
Используется для переноса данных при деплое на Railway
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_data():
    """Мигрирует данные из SQLite в PostgreSQL"""
    
    # URL базы данных
    sqlite_url = 'sqlite:///instance/tournament.db'
    postgres_url = os.environ.get('DATABASE_URL')
    
    if not postgres_url:
        logger.error("DATABASE_URL не установлен")
        return False
    
    try:
        # Подключение к SQLite
        sqlite_engine = create_engine(sqlite_url)
        sqlite_session = sessionmaker(bind=sqlite_engine)()
        
        # Подключение к PostgreSQL
        postgres_engine = create_engine(postgres_url)
        postgres_session = sessionmaker(bind=postgres_engine)()
        
        logger.info("Начинаем миграцию данных...")
        
        # Список таблиц для миграции
        tables = ['user', 'tournament', 'participant', 'match', 'notification', 'match_log']
        
        for table in tables:
            try:
                # Получаем данные из SQLite
                result = sqlite_session.execute(text(f"SELECT * FROM {table}"))
                rows = result.fetchall()
                
                if rows:
                    logger.info(f"Мигрируем {len(rows)} записей из таблицы {table}")
                    
                    # Получаем названия колонок
                    columns = result.keys()
                    
                    # Вставляем данные в PostgreSQL
                    for row in rows:
                        values = dict(zip(columns, row))
                        
                        # Формируем INSERT запрос
                        columns_str = ', '.join(columns)
                        placeholders = ', '.join([f':{col}' for col in columns])
                        insert_query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders})"
                        
                        try:
                            postgres_session.execute(text(insert_query), values)
                        except Exception as e:
                            logger.warning(f"Ошибка при вставке записи в {table}: {e}")
                            continue
                    
                    postgres_session.commit()
                    logger.info(f"Таблица {table} успешно мигрирована")
                else:
                    logger.info(f"Таблица {table} пуста, пропускаем")
                    
            except Exception as e:
                logger.error(f"Ошибка при миграции таблицы {table}: {e}")
                continue
        
        logger.info("Миграция завершена успешно!")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка миграции: {e}")
        return False
    
    finally:
        # Закрываем соединения
        if 'sqlite_session' in locals():
            sqlite_session.close()
        if 'postgres_session' in locals():
            postgres_session.close()

if __name__ == '__main__':
    success = migrate_data()
    sys.exit(0 if success else 1)
