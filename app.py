from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from flask_mail import Mail
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import logging
import secrets

# Импорт моделей из модулей
from models import db, User, Tournament, Participant, Match, Notification, MatchLog, Token, WaitingList, Settings, Player, UserActivity, Rally

# Импорт и регистрация маршрутов
from routes import register_routes

app = Flask(__name__)

# Импортируем конфигурацию
from config import DevelopmentConfig, ProductionConfig

# Определяем окружение
if os.environ.get('FLASK_ENV') == 'production':
    app.config.from_object(ProductionConfig)
else:
    app.config.from_object(DevelopmentConfig)

# Настройка префикса для dev окружения (если работает под /new_dev)
# Префикс устанавливается ТОЛЬКО через заголовок X-Script-Name от Nginx
# или через переменную окружения FORCE_SCRIPT_NAME
# Локально префикс НЕ устанавливается автоматически
script_name = os.environ.get('FORCE_SCRIPT_NAME', '')
if script_name:
    app.config['APPLICATION_ROOT'] = script_name

# Переопределяем некоторые настройки для совместимости
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'tournament-system-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'

# Настройки сессий для Railway
app.config['SESSION_COOKIE_SECURE'] = False  # Для HTTP (Railway может не иметь HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Настройка префикса для dev окружения (работа под /new_dev)
# Обрабатываем заголовок X-Script-Name от Nginx
from werkzeug.middleware.proxy_fix import ProxyFix

# Middleware для обработки префикса из заголовка X-Script-Name
class ScriptNameMiddleware:
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Получаем префикс из заголовка X-Script-Name от Nginx (только на сервере)
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
        # Проверяем переменную окружения FORCE_SCRIPT_NAME (для явного указания префикса)
        elif os.environ.get('FORCE_SCRIPT_NAME'):
            environ['SCRIPT_NAME'] = os.environ.get('FORCE_SCRIPT_NAME')
        # Временное решение: если работаем на порту 5001 (dev версия на сервере), устанавливаем префикс
        # Это нужно, если Nginx не передает заголовок X-Script-Name
        elif os.environ.get('PORT') == '5001' and os.environ.get('FLASK_ENV') != 'production':
            # Проверяем, что это не локальный запуск (localhost)
            server_name = environ.get('SERVER_NAME', '')
            http_host = environ.get('HTTP_HOST', '')
            # Если это не localhost, устанавливаем префикс
            if 'localhost' not in server_name.lower() and '127.0.0.1' not in http_host:
                environ['SCRIPT_NAME'] = '/new_dev'
        # НЕ устанавливаем префикс автоматически для локального запуска
        # Префикс устанавливается ТОЛЬКО через Nginx заголовок, FORCE_SCRIPT_NAME или порт 5001 на сервере
        
        return self.app(environ, start_response)

# Применяем middleware
app.wsgi_app = ScriptNameMiddleware(app.wsgi_app)
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1, x_host=1, x_proto=1, x_port=1, x_for=1)

# Устанавливаем APPLICATION_ROOT для правильной генерации URL
# Это нужно для того, чтобы url_for() учитывал префикс
@app.before_request
def set_script_root():
    from flask import request
    script_name = request.environ.get('SCRIPT_NAME', '')
    if script_name:
        app.config['APPLICATION_ROOT'] = script_name

# Контекстный процессор для добавления префикса в шаблоны
@app.context_processor
def inject_script_root():
    from flask import request
    try:
        # Получаем префикс из environ (устанавливается middleware из заголовка X-Script-Name от Nginx)
        # или из переменной окружения FORCE_SCRIPT_NAME
        script_name = request.environ.get('SCRIPT_NAME', '')
        
        # Логирование для отладки (только на dev сервере)
        if os.environ.get('FLASK_ENV') == 'development' or os.environ.get('PORT') == '5001':
            logger.debug(f"inject_script_root: SCRIPT_NAME={script_name}, HTTP_X_SCRIPT_NAME={request.environ.get('HTTP_X_SCRIPT_NAME', '')}")
        
        # Префикс устанавливается ТОЛЬКО через:
        # 1. Заголовок X-Script-Name от Nginx (на сервере)
        # 2. Переменную окружения FORCE_SCRIPT_NAME (для явного указания)
        # Локально (без заголовка и без FORCE_SCRIPT_NAME) префикс будет пустым
    except RuntimeError:
        # Если request context недоступен, возвращаем пустую строку
        script_name = ''
    return dict(script_root=script_name, base_path=script_name)

# Настройки email (переопределяем для локальной разработки)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tournaments.master@gmail.com'
app.config['MAIL_PASSWORD'] = 'jqjahujrmrnyzfbo'
app.config['MAIL_DEFAULT_SENDER'] = 'tournaments.master@gmail.com'

# Инициализация CSRF-защиты
csrf = CSRFProtect(app)

# Инициализация Flask-Mail
mail = Mail(app)

# Форма для входа
class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

# Настройка логирования
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
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Импорт и регистрация маршрутов
register_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, Token, WaitingList, Settings, Player, Rally)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Функция инициализации базы данных
def init_db():
    with app.app_context():
        try:
            # Создаем все таблицы
            db.create_all()
            logger.info("База данных инициализирована успешно")
            # Лёгкая миграция: добавить столбец tokens.telegram, если его нет
            try:
                from sqlalchemy import text
                conn = db.engine.connect()
                cols = conn.execute(text("PRAGMA table_info('tokens')")).fetchall()
                col_names = {c[1] for c in cols}
                if 'telegram' not in col_names:
                    conn.execute(text("ALTER TABLE tokens ADD COLUMN telegram VARCHAR(100)"))
                    logger.info("Добавлен столбец 'telegram' в таблицу tokens")
                if 'telegram_chat_id' not in col_names:
                    conn.execute(text("ALTER TABLE tokens ADD COLUMN telegram_chat_id VARCHAR(32)"))
                    logger.info("Добавлен столбец 'telegram_chat_id' в таблицу tokens")
                if 'telegram_link_token' not in col_names:
                    conn.execute(text("ALTER TABLE tokens ADD COLUMN telegram_link_token VARCHAR(128)"))
                    logger.info("Добавлен столбец 'telegram_link_token' в таблицу tokens")
                conn.close()
            except Exception as mig_e:
                logger.warning(f"Миграция tokens.telegram пропущена: {mig_e}")
            
            # Лёгкая миграция: добавить столбец participant.telegram, если его нет
            try:
                from sqlalchemy import text
                conn = db.engine.connect()
                # Проверяем таблицу participant
                cols = conn.execute(text("PRAGMA table_info('participant')")).fetchall()
                col_names = {c[1] for c in cols}
                if 'telegram' not in col_names:
                    conn.execute(text("ALTER TABLE participant ADD COLUMN telegram VARCHAR(100)"))
                    logger.info("Добавлен столбец 'telegram' в таблицу participant")
                # Проверяем таблицу waiting_list
                cols_waiting = conn.execute(text("PRAGMA table_info('waiting_list')")).fetchall()
                col_names_waiting = {c[1] for c in cols_waiting}
                if 'telegram' not in col_names_waiting:
                    conn.execute(text("ALTER TABLE waiting_list ADD COLUMN telegram VARCHAR(100)"))
                    logger.info("Добавлен столбец 'telegram' в таблицу waiting_list")
                if 'telegram_token' not in col_names_waiting:
                    conn.execute(text("ALTER TABLE waiting_list ADD COLUMN telegram_token VARCHAR(100)"))
                    logger.info("Добавлен столбец 'telegram_token' в таблицу waiting_list")
                if 'status' not in col_names_waiting:
                    conn.execute(text("ALTER TABLE waiting_list ADD COLUMN status VARCHAR(20) DEFAULT 'ожидает'"))
                    logger.info("Добавлен столбец 'status' в таблицу waiting_list")
                if 'created_at' not in col_names_waiting:
                    conn.execute(text("ALTER TABLE waiting_list ADD COLUMN created_at DATETIME"))
                    logger.info("Добавлен столбец 'created_at' в таблицу waiting_list")
                conn.close()
            except Exception as mig_e:
                logger.warning(f"Миграция participant.telegram пропущена: {mig_e}")
            
            # Лёгкая миграция: добавить столбцы actual_start_time и actual_end_time в таблицу match, если их нет
            try:
                from sqlalchemy import text
                conn = db.engine.connect()
                cols_match = conn.execute(text("PRAGMA table_info('match')")).fetchall()
                col_names_match = {c[1] for c in cols_match}
                if 'actual_start_time' not in col_names_match:
                    conn.execute(text("ALTER TABLE match ADD COLUMN actual_start_time DATETIME"))
                    logger.info("Добавлен столбец 'actual_start_time' в таблицу match")
                if 'actual_end_time' not in col_names_match:
                    conn.execute(text("ALTER TABLE match ADD COLUMN actual_end_time DATETIME"))
                    logger.info("Добавлен столбец 'actual_end_time' в таблицу match")
                conn.close()
            except Exception as mig_e:
                logger.warning(f"Миграция match.actual_start_time пропущена: {mig_e}")
            
            # Создание/обновление администратора по умолчанию
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', password_hash=generate_password_hash('adm555'), role='администратор')
                db.session.add(admin)
                db.session.commit()
                logger.info("Администратор создан: admin/adm555")
            else:
                # Обновляем пароль администратора на случай, если он был изменен
                admin.password_hash = generate_password_hash('adm555')
                db.session.commit()
                logger.info("Пароль администратора обновлен: admin/adm555")
            
            # Инициализация настроек по умолчанию
            Settings.set_setting('max_tokens', '10', 'Максимальное количество паролей для создания турниров')
            logger.info("Настройки по умолчанию инициализированы")
                
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            # На Railway может не быть прав на запись, попробуем альтернативный путь
            try:
                import tempfile
                temp_db_path = os.path.join(tempfile.gettempdir(), 'tournament.db')
                app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_db_path}'
                db.create_all()
                logger.info(f"База данных создана в временной папке: {temp_db_path}")
            except Exception as e2:
                logger.error(f"Критическая ошибка создания базы данных: {e2}")

# Обработчик ошибок для отладки
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}")
    return "Internal Server Error", 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"Not Found Error: {error}")
    return "Not Found", 404

# Инициализация базы данных при импорте (для Railway)
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Запуск приложения на порту {port}")
    logger.info(f"Переменная окружения PORT: {os.environ.get('PORT')}")
    logger.info(f"Режим отладки: {os.environ.get('FLASK_ENV', 'production')}")
    app.run(debug=True, host='0.0.0.0', port=port)
