from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import logging
import secrets
import sqlite3
from sqlalchemy import create_engine, text, inspect

# Импорт конфигурации
from config import DevelopmentConfig, ProductionConfig

# Импорт моделей из модулей
from models import create_models

# Импорт и регистрация маршрутов
from routes import register_routes

def migrate_database():
    """Выполняет миграцию базы данных, добавляя недостающие колонки"""
    try:
        # Получаем URL базы данных
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        print(f"🔧 Выполняем миграцию базы данных: {db_uri}")
        
        # Создаем подключение
        engine = create_engine(db_uri)
        
        with engine.connect() as conn:
            # Проверяем существование таблиц
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            print(f"📋 Найденные таблицы: {tables}")
            
            # Добавляем колонку points в таблицу participant
            if 'participant' in tables:
                try:
                    # Проверяем, существует ли колонка points
                    columns = inspector.get_columns('participant')
                    column_names = [col['name'] for col in columns]
                    
                    if 'points' not in column_names:
                        print("➕ Добавляем колонку 'points' в таблицу 'participant'...")
                        conn.execute(text("ALTER TABLE participant ADD COLUMN points INTEGER DEFAULT 0"))
                        conn.commit()
                        print("✅ Колонка 'points' успешно добавлена")
                    else:
                        print("✅ Колонка 'points' уже существует в таблице 'participant'")
                        
                except Exception as e:
                    print(f"❌ Ошибка при добавлении колонки 'points': {e}")
            
            # Добавляем колонки для сетов в таблицу match
            if 'match' in tables:
                try:
                    columns = inspector.get_columns('match')
                    column_names = [col['name'] for col in columns]
                    
                    # Добавляем колонки для сетов
                    set_columns = [
                        'set1_score1', 'set1_score2',
                        'set2_score1', 'set2_score2', 
                        'set3_score1', 'set3_score2'
                    ]
                    
                    for col in set_columns:
                        if col not in column_names:
                            print(f"➕ Добавляем колонку '{col}' в таблицу 'match'...")
                            conn.execute(text(f"ALTER TABLE match ADD COLUMN {col} INTEGER DEFAULT 0"))
                            conn.commit()
                            print(f"✅ Колонка '{col}' успешно добавлена")
                        else:
                            print(f"✅ Колонка '{col}' уже существует в таблице 'match'")
                            
                except Exception as e:
                    print(f"❌ Ошибка при добавлении колонок сетов: {e}")
        
        print("🎉 Миграция базы данных завершена успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при миграции базы данных: {e}")
        return False

def check_missing_fields():
    """Проверяет и выводит недостающие поля в базе данных"""
    try:
        # Получаем путь к базе данных из конфигурации
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            if not os.path.exists(db_path):
                print("❌ База данных не найдена!")
                return
            
            print(f"🔍 Проверяем базу данных: {db_path}")
            
            # Подключаемся к базе данных
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Определяем ожидаемые поля для каждой таблицы
            expected_fields = {
                'user': ['id', 'username', 'password_hash', 'role', 'created_at'],
                'tournament': ['id', 'name', 'description', 'start_date', 'end_date', 'max_participants', 
                              'court_count', 'match_duration', 'break_duration', 'sets_to_win', 
                              'points_to_win', 'points_win', 'points_draw', 'points_loss', 
                              'start_time', 'end_time', 'created_at', 'created_by'],
                'participant': ['id', 'tournament_id', 'user_id', 'name', 'is_team', 'points', 'registered_at'],
                'match': ['id', 'tournament_id', 'participant1_id', 'participant2_id', 'match_date', 
                         'match_time', 'court_number', 'match_number', 'score1', 'score2', 'score', 
                         'sets_won_1', 'sets_won_2', 'winner_id', 'status', 'created_at', 'updated_at',
                         'set1_score1', 'set1_score2', 'set2_score1', 'set2_score2', 'set3_score1', 'set3_score2'],
                'notification': ['id', 'user_id', 'message', 'is_read', 'created_at'],
                'match_log': ['id', 'match_id', 'action', 'details', 'created_at']
            }
            
            missing_fields = {}
            
            # Проверяем каждую таблицу
            for table_name, expected_columns in expected_fields.items():
                try:
                    # Получаем структуру таблицы
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    existing_columns = [row[1] for row in cursor.fetchall()]
                    
                    # Находим недостающие поля
                    missing = [col for col in expected_columns if col not in existing_columns]
                    
                    if missing:
                        missing_fields[table_name] = missing
                        print(f"❌ Таблица '{table_name}' - недостающие поля: {', '.join(missing)}")
                    else:
                        print(f"✅ Таблица '{table_name}' - все поля на месте")
                        
                except sqlite3.OperationalError as e:
                    if "no such table" in str(e):
                        print(f"❌ Таблица '{table_name}' не существует")
                        missing_fields[table_name] = expected_columns
                    else:
                        print(f"❌ Ошибка при проверке таблицы '{table_name}': {e}")
            
            conn.close()
            
            # Выводим итоговый отчет
            if missing_fields:
                print(f"\n📋 ИТОГОВЫЙ ОТЧЕТ:")
                print(f"🔴 Найдено {len(missing_fields)} таблиц с недостающими полями:")
                for table, fields in missing_fields.items():
                    print(f"   - {table}: {', '.join(fields)}")
            else:
                print(f"\n✅ ВСЕ ПОЛЯ НА МЕСТЕ! База данных соответствует моделям.")
            
            return missing_fields
            
    except Exception as e:
        print(f"❌ Ошибка при проверке полей: {e}")
        return {}

app = Flask(__name__)

# Выбор конфигурации в зависимости от окружения
if os.environ.get('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Устанавливаем FLASK_ENV для корректной работы
if not os.environ.get('FLASK_ENV'):
    os.environ['FLASK_ENV'] = 'development'

# Инициализация CSRF-защиты
csrf = CSRFProtect(app)

# Форма для входа
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

# Настройка логирования
if os.environ.get('FLASK_ENV') == 'production':
    # Логирование для продакшена (Railway)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]  # Только в консоль для Railway
    )
else:
    # Логирование для разработки
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )
logger = logging.getLogger(__name__)

# Инициализация базы данных
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Создание моделей с текущим экземпляром db
models = create_models(db)
User = models['User']
Tournament = models['Tournament']
Participant = models['Participant']
Match = models['Match']
Notification = models['Notification']
MatchLog = models['MatchLog']

# Импорт и регистрация маршрутов
register_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Маршрут для экспорта в Excel
@app.route('/tournament/<int:tournament_id>/export')
@login_required
def export_tournament(tournament_id):
    """Экспорт турнира в Excel"""
    try:
        from routes.export import create_excel_export
        from routes.main import calculate_statistics, calculate_participant_positions
        
        tournament = Tournament.query.get_or_404(tournament_id)
        participants = Participant.query.filter_by(tournament_id=tournament_id).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).all()
        
        # Сортируем участников по имени
        participants.sort(key=lambda x: x.name)
        
        # Создаем статистику и рассчитываем места участников
        statistics = calculate_statistics(participants, matches, tournament)
        positions = calculate_participant_positions(participants, statistics)
        
        # Создаем Excel файл
        filepath, filename = create_excel_export(tournament, participants, matches, statistics, positions)
        
        flash(f'Турнир успешно экспортирован в файл {filename}', 'success')
        
        # Отправляем файл пользователю
        return send_file(filepath, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Ошибка при экспорте турнира: {e}")
        flash(f'Ошибка при экспорте турнира: {str(e)}', 'error')
        return redirect(url_for('tournament_detail', tournament_id=tournament_id))

# Миграция будет выполнена в функции init_db()

# Функция инициализации базы данных
def init_db():
    with app.app_context():
        try:
            # Сначала выполняем миграцию базы данных
            print("\n" + "="*60)
            print("🔧 ВЫПОЛНЕНИЕ МИГРАЦИИ БАЗЫ ДАННЫХ")
            print("="*60)
            migrate_database()
            print("="*60 + "\n")
            
            # Создаем таблицы
            db.create_all()
            
            # Создание администратора по умолчанию
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', password_hash=generate_password_hash('admin123'), role='администратор')
                db.session.add(admin)
                db.session.commit()
                print("Администратор создан: admin/admin123")
        except Exception as e:
            print(f"Ошибка инициализации базы данных: {e}")
            # Продолжаем работу, возможно база уже инициализирована

if __name__ == '__main__':
    # Инициализация базы данных только при запуске приложения
    init_db()
    
    # Проверяем недостающие поля в базе данных
    print("\n" + "="*60)
    print("🔍 ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("="*60)
    check_missing_fields()
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
