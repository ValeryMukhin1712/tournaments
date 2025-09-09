from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
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

# Импорт моделей из модулей
from models import create_models

# Импорт и регистрация маршрутов
from routes import register_routes

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация CSRF-защиты
csrf = CSRFProtect(app)

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

# Импорт и регистрация маршрутов
register_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Функция инициализации базы данных
def init_db():
    with app.app_context():
        db.create_all()
        
        # Создание администратора по умолчанию
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', password_hash=generate_password_hash('admin123'), role='администратор')
            db.session.add(admin)
            db.session.commit()
            print("Администратор создан: admin/admin123")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
