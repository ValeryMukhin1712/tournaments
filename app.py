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
from models import create_models

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

# Переопределяем некоторые настройки для совместимости
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'tournament-system-secret-key-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'

# Настройки сессий для Railway
app.config['SESSION_COOKIE_SECURE'] = False  # Для HTTP (Railway может не иметь HTTPS)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
Token = models['Token']

# Импорт и регистрация маршрутов
register_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, Token)

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
            
            # Создание/обновление администратора по умолчанию
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(username='admin', password_hash=generate_password_hash('adm444'), role='администратор')
                db.session.add(admin)
                db.session.commit()
                logger.info("Администратор создан: admin/adm444")
            else:
                # Обновляем пароль администратора на случай, если он был изменен
                admin.password_hash = generate_password_hash('adm444')
                db.session.commit()
                logger.info("Пароль администратора обновлен: admin/adm444")
                
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
