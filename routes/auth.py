"""
Маршруты аутентификации
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import check_password_hash
import logging

logger = logging.getLogger(__name__)

def create_auth_routes(app, db, User):
    """Создает маршруты аутентификации"""
    
    # Форма для входа
    class LoginForm(FlaskForm):
        username = StringField('Имя пользователя', validators=[DataRequired()])
        password = PasswordField('Пароль', validators=[DataRequired()])
        submit = SubmitField('Войти')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            
            logger.info(f"Попытка входа пользователя: {username}")
            
            user = User.query.filter_by(username=username).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                logger.info(f"Успешный вход пользователя: {username} (ID: {user.id}, Роль: {user.role})")
                flash(f'Добро пожаловать, {username}!', 'success')
                return redirect(url_for('index'))
            else:
                logger.warning(f"Неудачная попытка входа для пользователя: {username}")
                flash('Неверное имя пользователя или пароль', 'error')
        
        return render_template('login.html', form=form)

    @app.route('/logout')
    @login_required
    def logout():
        username = current_user.username
        logout_user()
        logger.info(f"Участник {username} вышел из системы")
        flash('Вы успешно вышли из системы', 'info')
        return redirect(url_for('login'))