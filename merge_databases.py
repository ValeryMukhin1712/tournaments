#!/usr/bin/env python3
"""
Скрипт для слияния двух баз данных SQLite

Использование:
    python merge_databases.py --source instance/tournament.db --target instance/tournament_server.db --output instance/tournament_merged.db

Опции:
    --source: путь к исходной БД (локальная)
    --target: путь к целевой БД (серверная)
    --output: путь к результирующей БД (по умолчанию: instance/tournament_merged.db)
    --backup: создать бэкап целевой БД перед слиянием (по умолчанию: True)
"""

import sqlite3
import argparse
import os
import shutil
from datetime import datetime
from collections import defaultdict

class DatabaseMerger:
    def __init__(self, source_db, target_db, output_db, create_backup=True):
        self.source_db = source_db
        self.target_db = target_db
        self.output_db = output_db
        self.create_backup = create_backup
        
        # Маппинг старых ID на новые ID для каждой таблицы
        self.id_mappings = defaultdict(dict)
        
        # Порядок таблиц для обработки (сначала независимые, потом зависимые)
        self.table_order = [
            # Независимые таблицы
            'user',
            'player',
            'settings',
            'token',
            'notification',
            'waiting_list',
            'user_activity',
            # Зависимые таблицы (в порядке зависимостей)
            'tournament',
            'participant',
            'match',
            'match_log',
            'rally'
        ]
        
    def create_backup_file(self):
        """Создает бэкап целевой БД"""
        if not os.path.exists(self.target_db):
            print(f"⚠️  Целевая БД {self.target_db} не существует, пропускаем бэкап")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.target_db}.backup_{timestamp}"
        shutil.copy2(self.target_db, backup_path)
        print(f"✅ Создан бэкап: {backup_path}")
        return backup_path
    
    def get_table_columns(self, conn, table_name):
        """Получает список колонок таблицы"""
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]
    
    def get_table_data(self, conn, table_name):
        """Получает все данные из таблицы"""
        try:
            cursor = conn.execute(f"SELECT * FROM {table_name}")
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()
            return columns, rows
        except sqlite3.OperationalError as e:
            print(f"⚠️  Таблица {table_name} не существует или недоступна: {e}")
            return None, []
    
    def get_unique_key(self, table_name, row, columns):
        """Определяет уникальный ключ для записи"""
        # Для таблиц с уникальными полями используем их
        unique_fields = {
            'tournament': ['name'],
            'user': ['username'],
            'player': ['name'],
            'token': ['token'],
            'settings': ['key'],
        }
        
        if table_name in unique_fields:
            key_parts = []
            for field in unique_fields[table_name]:
                if field in columns:
                    try:
                        idx = columns.index(field)
                        value = row[idx] if idx < len(row) else None
                        key_parts.append(str(value) if value is not None else '')
                    except (ValueError, IndexError):
                        continue
            if key_parts and any(key_parts):  # Проверяем, что есть хотя бы одно непустое значение
                return tuple(key_parts)
        
        # По умолчанию используем ID
        if 'id' in columns:
            try:
                idx = columns.index('id')
                if idx < len(row):
                    return row[idx]
            except (ValueError, IndexError):
                pass
        
        # Если ничего не подошло, используем всю строку как ключ
        return tuple(str(v) if v is not None else '' for v in row)
    
    def merge_table(self, source_conn, target_conn, output_conn, table_name):
        """Объединяет данные таблицы из двух БД"""
        print(f"\n📊 Обработка таблицы: {table_name}")
        
        # Получаем данные из обеих БД
        source_columns, source_rows = self.get_table_data(source_conn, table_name)
        target_columns, target_rows = self.get_table_data(target_conn, table_name)
        
        if source_columns is None and target_columns is None:
            print(f"  ⚠️  Таблица {table_name} отсутствует в обеих БД, пропускаем")
            return
        
        # Определяем колонки (используем из той БД, где таблица есть)
        columns = source_columns if source_columns else target_columns
        if not columns:
            print(f"  ⚠️  Не удалось определить колонки для {table_name}")
            return
        
        # Получаем текущие записи из результирующей БД
        output_columns, output_rows = self.get_table_data(output_conn, table_name)
        if output_columns is None:
            output_columns = columns
            output_rows = []
        
        # Создаем словарь существующих записей в результирующей БД по уникальному ключу
        existing_records = {}
        existing_ids = set()
        id_idx = columns.index('id') if 'id' in columns else None
        
        for row in output_rows:
            if id_idx is not None:
                existing_ids.add(row[id_idx])
            key = self.get_unique_key(table_name, row, columns)
            if key is not None:
                existing_records[key] = row
        
        # Получаем максимальный ID в результирующей БД
        max_id = max(existing_ids) if existing_ids else 0
        
        # Обрабатываем записи из исходной БД
        new_records = []
        updated_count = 0
        inserted_count = 0
        skipped_count = 0
        
        for source_row in source_rows:
            key = self.get_unique_key(table_name, source_row, columns)
            
            if key in existing_records:
                # Запись уже существует - пропускаем (используем данные из целевой БД)
                skipped_count += 1
                continue
            else:
                # Новая запись - добавляем с обновлением ID и foreign keys
                new_row = list(source_row)
                
                # Обновляем ID, если нужно
                if id_idx is not None:
                    old_id = new_row[id_idx]
                    if old_id is not None and old_id in existing_ids:
                        # ID конфликтует - генерируем новый
                        max_id += 1
                        new_id = max_id
                        # Сохраняем маппинг для обновления foreign keys
                        self.id_mappings[table_name][old_id] = new_id
                        new_row[id_idx] = new_id
                    elif old_id is not None:
                        # ID свободен - сохраняем маппинг
                        self.id_mappings[table_name][old_id] = old_id
                        existing_ids.add(old_id)
                
                # Обновляем foreign keys
                new_row = list(self.update_foreign_keys(new_row, columns, table_name))
                new_records.append(tuple(new_row))
                inserted_count += 1
        
        # Добавляем записи, которые есть только в целевой БД (они уже в результирующей)
        # Но проверяем, нет ли новых записей в целевой БД, которых нет в результирующей
        target_keys = {self.get_unique_key(table_name, row, columns) for row in target_rows}
        for target_row in target_rows:
            key = self.get_unique_key(table_name, target_row, columns)
            if key not in existing_records and key not in {self.get_unique_key(table_name, row, columns) for row in new_records}:
                new_row = list(target_row)
                # Обновляем foreign keys
                new_row = list(self.update_foreign_keys(new_row, columns, table_name))
                new_records.append(tuple(new_row))
                inserted_count += 1
        
        # Вставляем новые записи в результирующую БД
        if new_records:
            self.insert_records(output_conn, table_name, columns, new_records)
        
        print(f"  ✅ Обработано: {len(existing_records) + len(new_records)} записей ({inserted_count} новых, {skipped_count} пропущено)")
    
    def merge_row(self, table_name, source_row, target_row, columns):
        """Объединяет две строки одной таблицы"""
        # По умолчанию используем данные из целевой БД (более свежие)
        # Но можно настроить логику слияния для конкретных полей
        return target_row
    
    def update_foreign_keys(self, row, columns, table_name):
        """Обновляет foreign keys в строке согласно маппингу ID"""
        updated_row = list(row)
        
        # Маппинг foreign keys для каждой таблицы
        fk_mappings = {
            'participant': {
                'tournament_id': 'tournament',
                'user_id': 'user'
            },
            'match': {
                'tournament_id': 'tournament',
                'participant1_id': 'participant',
                'participant2_id': 'participant',
                'winner_id': 'participant'
            },
            'rally': {
                'match_id': 'match',
                'tournament_id': 'tournament'
            },
            'match_log': {
                'match_id': 'match',
                'tournament_id': 'tournament'
            }
        }
        
        if table_name in fk_mappings:
            for fk_column, ref_table in fk_mappings[table_name].items():
                if fk_column in columns:
                    idx = columns.index(fk_column)
                    old_id = updated_row[idx]
                    if old_id is not None and old_id in self.id_mappings[ref_table]:
                        updated_row[idx] = self.id_mappings[ref_table][old_id]
        
        return tuple(updated_row)
    
    def insert_records(self, conn, table_name, columns, rows):
        """Вставляет записи в таблицу"""
        if not rows:
            return
        
        # Создаем таблицу, если её нет
        self.create_table_if_not_exists(conn, table_name, columns)
        
        # Подготавливаем данные для вставки
        placeholders = ','.join(['?' for _ in columns])
        
        for row in rows:
            # Вставляем запись
            try:
                conn.execute(
                    f"INSERT OR IGNORE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})",
                    row
                )
            except sqlite3.IntegrityError as e:
                # Если ошибка уникальности, пробуем REPLACE
                try:
                    conn.execute(
                        f"INSERT OR REPLACE INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})",
                        row
                    )
                except Exception as e2:
                    print(f"  ⚠️  Ошибка вставки в {table_name}: {e2}")
                    continue
            except Exception as e:
                print(f"  ⚠️  Ошибка вставки в {table_name}: {e}")
                continue
        
        conn.commit()
    
    def create_table_if_not_exists(self, conn, table_name, columns):
        """Создает таблицу, если её нет"""
        # Получаем структуру таблицы из исходной БД
        source_conn = sqlite3.connect(self.source_db)
        cursor = source_conn.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        result = cursor.fetchone()
        source_conn.close()
        
        if result:
            create_sql = result[0]
            # Заменяем CREATE TABLE на CREATE TABLE IF NOT EXISTS
            create_sql = create_sql.replace('CREATE TABLE', 'CREATE TABLE IF NOT EXISTS')
            try:
                conn.execute(create_sql)
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Таблица уже существует
    
    def merge(self):
        """Выполняет слияние БД"""
        print("=" * 60)
        print("🔄 Слияние баз данных")
        print("=" * 60)
        
        # Проверяем существование исходных БД
        if not os.path.exists(self.source_db):
            print(f"❌ Исходная БД не найдена: {self.source_db}")
            return False
        
        if not os.path.exists(self.target_db):
            print(f"⚠️  Целевая БД не найдена: {self.target_db}")
            print("   Создаем новую БД на основе исходной...")
            shutil.copy2(self.source_db, self.output_db)
            print(f"✅ Создана БД: {self.output_db}")
            return True
        
        # Создаем бэкап
        if self.create_backup:
            self.create_backup_file()
        
        # Копируем целевую БД как основу для результата
        shutil.copy2(self.target_db, self.output_db)
        print(f"\n✅ Создана результирующая БД: {self.output_db}")
        
        # Открываем соединения
        source_conn = sqlite3.connect(self.source_db)
        target_conn = sqlite3.connect(self.target_db)
        output_conn = sqlite3.connect(self.output_db)
        
        try:
            # Обрабатываем таблицы в порядке зависимостей
            for table_name in self.table_order:
                try:
                    self.merge_table(source_conn, target_conn, output_conn, table_name)
                except Exception as e:
                    print(f"  ❌ Ошибка при обработке {table_name}: {e}")
                    continue
            
            # Обрабатываем остальные таблицы (если есть)
            source_tables = set()
            target_tables = set()
            
            cursor = source_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            source_tables.update(row[0] for row in cursor.fetchall())
            
            cursor = target_conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            target_tables.update(row[0] for row in cursor.fetchall())
            
            all_tables = source_tables | target_tables
            remaining_tables = all_tables - set(self.table_order)
            
            for table_name in remaining_tables:
                try:
                    self.merge_table(source_conn, target_conn, output_conn, table_name)
                except Exception as e:
                    print(f"  ❌ Ошибка при обработке {table_name}: {e}")
                    continue
            
            print("\n" + "=" * 60)
            print("✅ Слияние завершено успешно!")
            print("=" * 60)
            print(f"\n📁 Результирующая БД: {self.output_db}")
            print("\n⚠️  ВАЖНО: Проверьте результат перед использованием!")
            print("   Рекомендуется протестировать приложение с новой БД.")
            
            return True
            
        finally:
            source_conn.close()
            target_conn.close()
            output_conn.close()


def main():
    parser = argparse.ArgumentParser(description='Слияние двух баз данных SQLite')
    parser.add_argument('--source', required=True, help='Путь к исходной БД (локальная)')
    parser.add_argument('--target', required=True, help='Путь к целевой БД (серверная)')
    parser.add_argument('--output', default='instance/tournament_merged.db', help='Путь к результирующей БД')
    parser.add_argument('--no-backup', action='store_true', help='Не создавать бэкап целевой БД')
    
    args = parser.parse_args()
    
    # Создаем директорию для output, если её нет
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    merger = DatabaseMerger(
        source_db=args.source,
        target_db=args.target,
        output_db=args.output,
        create_backup=not args.no_backup
    )
    
    success = merger.merge()
    exit(0 if success else 1)


if __name__ == '__main__':
    main()

