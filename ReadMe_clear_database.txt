# Инструкция по очистке базы данных и исправлению ошибок SQLAlchemy

## Проблема
Ошибка: `sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: match.score`

Эта ошибка возникает когда SQLAlchemy кэширует схему базы данных и не видит изменения в структуре таблиц.

## Решение

### Шаг 1: Остановить приложение
```bash
taskkill /f /im python.exe
```

### Шаг 2: Удалить все файлы базы данных
```bash
# Удаляем все возможные файлы базы данных
del tournament.db
del instance\tournament.db
del instance\tournaments_new.db
```

### Шаг 3: Очистить кэш Python
```bash
# Удаляем все __pycache__ директории
rmdir /s /q __pycache__
rmdir /s /q models\__pycache__
rmdir /s /q routes\__pycache__
rmdir /s /q services\__pycache__
rmdir /s /q utils\__pycache__

# Удаляем все .pyc файлы
for /r . %i in (*.pyc) do del "%i"
```

### Шаг 4: Пересоздать базу данных
Создать скрипт `recreate_db.py`:

```python
import os
import sqlite3
from werkzeug.security import generate_password_hash

def recreate_database():
    # Удаляем старые файлы
    db_files = ['tournament.db', 'instance/tournament.db']
    for db_file in db_files:
        if os.path.exists(db_file):
            os.remove(db_file)
    
    # Создаем директорию instance
    os.makedirs('instance', exist_ok=True)
    
    # Создаем новую базу данных
    conn = sqlite3.connect('tournament.db')
    cursor = conn.cursor()
    
    # Создаем все таблицы с правильной схемой
    cursor.execute('''
        CREATE TABLE user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash VARCHAR(120) NOT NULL,
            role VARCHAR(20) DEFAULT 'участник',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE tournament (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            start_date DATE,
            end_date DATE,
            max_participants INTEGER,
            court_count INTEGER DEFAULT 1,
            match_duration INTEGER DEFAULT 60,
            break_duration INTEGER DEFAULT 10,
            sets_to_win INTEGER DEFAULT 2,
            points_to_win INTEGER DEFAULT 21,
            points_win INTEGER DEFAULT 3,
            points_draw INTEGER DEFAULT 1,
            points_loss INTEGER DEFAULT 0,
            start_time TIME,
            end_time TIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE participant (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER,
            name VARCHAR(100) NOT NULL,
            is_team BOOLEAN DEFAULT FALSE,
            points INTEGER DEFAULT 0,
            registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE match (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            participant1_id INTEGER NOT NULL,
            participant2_id INTEGER NOT NULL,
            score1 INTEGER,
            score2 INTEGER,
            score VARCHAR(20),
            sets_won_1 INTEGER DEFAULT 0,
            sets_won_2 INTEGER DEFAULT 0,
            winner_id INTEGER,
            match_date DATE,
            match_time TIME,
            court_number INTEGER,
            match_number INTEGER,
            status VARCHAR(20) DEFAULT 'запланирован',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE notification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT FALSE,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE match_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER NOT NULL,
            action VARCHAR(50) NOT NULL,
            details TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Создаем администратора
    admin_password = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO user (username, password_hash, role) 
        VALUES ('admin', ?, 'администратор')
    ''', (admin_password,))
    
    conn.commit()
    conn.close()
    print("✅ База данных пересоздана!")

if __name__ == '__main__':
    recreate_database()
```

### Шаг 5: Запустить скрипт пересоздания
```bash
python recreate_db.py
```

### Шаг 6: Запустить приложение
```bash
python app.py
```

## Альтернативный быстрый способ

Если нужно быстро исправить проблему:

1. Остановить приложение: `taskkill /f /im python.exe`
2. Удалить базу: `del tournament.db`
3. Запустить приложение: `python app.py` (приложение само создаст базу с правильной схемой)

## Проверка результата

После выполнения всех шагов:
- ✅ Приложение должно запуститься без ошибок
- ✅ В логах должно быть: "✅ ВСЕ ПОЛЯ НА МЕСТЕ! База данных соответствует моделям."
- ✅ Можно войти как admin/admin123
- ✅ Все функции приложения должны работать

## Примечания

- Эта проблема часто возникает при изменении моделей SQLAlchemy
- Всегда делайте резервные копии базы данных перед изменениями
- После изменения моделей рекомендуется пересоздавать базу данных
- Кэш SQLAlchemy может мешать обновлению схемы, поэтому его нужно очищать

---
Создано: 13.09.2025
Проблема: SQLAlchemy кэширует схему базы данных
Решение: Полное пересоздание базы данных + очистка кэша
