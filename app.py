from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import os
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tournament.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tournament.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели базы данных
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='участник')  # участник, доверенный_участник, администратор
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sport_type = db.Column(db.String(50), nullable=False)  # теннис, бадминтон, волейбол
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    max_participants = db.Column(db.Integer, default=32)
    court_count = db.Column(db.Integer, default=3)  # количество площадок
    match_duration = db.Column(db.Integer, default=60)  # продолжительность матча в минутах
    break_duration = db.Column(db.Integer, default=15)  # перерыв между матчами в минутах
    points_win = db.Column(db.Integer, default=3)  # очки за победу
    points_draw = db.Column(db.Integer, default=1)  # очки за ничью
    points_loss = db.Column(db.Integer, default=0)  # очки за поражение
    points_to_win = db.Column(db.Integer, default=21)  # количество очков для победы в матче
    status = db.Column(db.String(20), default='регистрация')  # регистрация, активен, завершен
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    is_team = db.Column(db.Boolean, default=False)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

class Match(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    participant1_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    participant2_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    score1 = db.Column(db.Integer)
    score2 = db.Column(db.Integer)
    winner_id = db.Column(db.Integer, db.ForeignKey('participant.id'))
    match_date = db.Column(db.Date)
    match_time = db.Column(db.Time)
    court_number = db.Column(db.Integer)  # номер площадки
    status = db.Column(db.String(20), default='запланирован')  # запланирован, в_процессе, завершен
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи для отображения имен участников
    participant1 = db.relationship('Participant', foreign_keys=[participant1_id], backref='matches_as_p1')
    participant2 = db.relationship('Participant', foreign_keys=[participant2_id], backref='matches_as_p2')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MatchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # создан, изменен, удален
    old_score1 = db.Column(db.Integer)
    old_score2 = db.Column(db.Integer)
    new_score1 = db.Column(db.Integer)
    new_score2 = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создание таблиц
with app.app_context():
    db.create_all()
    
    # Создание администратора по умолчанию
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password_hash='admin123', role='администратор')
        db.session.add(admin)
        db.session.commit()

@app.route('/')
def index():
    tournaments = Tournament.query.all()
    # Загружаем участников для каждого турнира
    for tournament in tournaments:
        tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
    return render_template('index.html', tournaments=tournaments)

@app.route('/users')
@login_required
def users_list():
    """Страница со списком всех пользователей"""
    if current_user.role not in ['администратор', 'доверенный_участник']:
        flash('Недостаточно прав для просмотра списка пользователей', 'error')
        return redirect(url_for('index'))
    
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        logger.info(f"Попытка входа пользователя: {username}")
        
        user = User.query.filter_by(username=username).first()
        if user and user.password_hash == password:  # Простая проверка пароля
            login_user(user)
            logger.info(f"Успешный вход пользователя: {username} (ID: {user.id}, Роль: {user.role})")
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            logger.warning(f"Неудачная попытка входа пользователя: {username}")
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    user_id = current_user.id
    logout_user()
    logger.info(f"Выход пользователя: {username} (ID: {user_id})")
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

@app.route('/api/users', methods=['POST'])
def create_user():
    """Создание нового пользователя (регистрация)"""
    logger.info(f"ПОЛУЧЕН ЗАПРОС на /api/users")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request data: {request.get_data()}")
    
    data = request.get_json()
    logger.info(f"Parsed JSON data: {data}")
    
    username = data.get('username', 'неизвестно') if data else 'неизвестно'
    
    logger.info(f"Попытка регистрации пользователя: {username}")
    
    # Проверяем, не существует ли уже пользователь с таким именем
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        logger.warning(f"Попытка регистрации существующего пользователя: {username}")
        return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует'}), 400
    
    try:
        # Определяем роль пользователя
        role = data.get('role', 'участник')  # По умолчанию обычный участник
        
        # Проверяем права на создание администраторов
        if role == 'администратор' and (not current_user.is_authenticated or current_user.role != 'администратор'):
            logger.warning(f"Попытка создания администратора без прав: {username}")
            return jsonify({'success': False, 'error': 'Недостаточно прав для создания администратора'}), 403
        
        user = User(
            username=data['username'],
            password_hash=data['password'],  # В реальном приложении пароль нужно хешировать
            role=role
        )
        db.session.add(user)
        db.session.commit()
        
        # Автоматически входим в систему после успешной регистрации
        login_user(user)
        
        logger.info(f"Успешная регистрация пользователя: {username} (ID: {user.id}, Роль: {role})")
        
        return jsonify({
            'success': True, 
            'message': 'Пользователь успешно создан и выполнен вход в систему',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка при регистрации пользователя {username}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users/<int:user_id>/role', methods=['PUT'])
@login_required
def change_user_role(user_id):
    """Изменение роли пользователя"""
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для изменения роли'}), 403
    
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    try:
        user.role = data['role']
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Роль пользователя изменена'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    """Получение списка пользователей для добавления в турнир"""
    if current_user.role not in ['администратор', 'доверенный_участник']:
        return jsonify({'success': False, 'error': 'Недостаточно прав для просмотра списка пользователей'}), 403
    
    try:
        tournament_id = request.args.get('tournament_id', type=int)
        
        # Получаем всех пользователей
        users = User.query.order_by(User.username).all()
        
        # Если указан tournament_id, исключаем уже участвующих в турнире
        if tournament_id:
            existing_participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            existing_user_ids = {p.user_id for p in existing_participants}
            users = [user for user in users if user.id not in existing_user_ids]
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'role': user.role
            })
        
        return jsonify({'success': True, 'users': users_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Удаление пользователя"""
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для удаления пользователя'}), 403
    
    if current_user.id == user_id:
        return jsonify({'success': False, 'error': 'Нельзя удалить самого себя'}), 400
    
    user = User.query.get_or_404(user_id)
    
    try:
        # Удаляем все связанные данные
        Participant.query.filter_by(user_id=user_id).delete()
        MatchLog.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Пользователь удален'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments', methods=['POST'])
@login_required
def create_tournament():
    if current_user.role != 'администратор':
        logger.warning(f"Попытка создания турнира без прав администратора пользователем: {current_user.username}")
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    data = request.get_json()
    tournament_name = data.get('name', 'неизвестно')
    
    logger.info(f"Попытка создания турнира '{tournament_name}' пользователем: {current_user.username}")
    
    try:
        tournament = Tournament(
            name=data['name'],
            sport_type=data['sport_type'],
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date(),
            max_participants=int(data['max_participants']),
            court_count=int(data.get('court_count', 3)),
            match_duration=int(data.get('match_duration', 60)),
            break_duration=int(data.get('break_duration', 15)),
            points_win=int(data.get('points_win', 3)),
            points_draw=int(data.get('points_draw', 1)),
            points_loss=int(data.get('points_loss', 0)),
            points_to_win=int(data.get('points_to_win', 21))
        )
        db.session.add(tournament)
        db.session.commit()
        
        logger.info(f"Успешное создание турнира '{tournament_name}' (ID: {tournament.id}) пользователем: {current_user.username}")
        
        return jsonify({'success': True, 'tournament_id': tournament.id})
    except Exception as e:
        logger.error(f"Ошибка при создании турнира '{tournament_name}': {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/participants', methods=['POST'])
def add_participant(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    data = request.get_json()
    
    participant_name = data.get('name', 'неизвестно')
    user_info = f" (пользователь: {current_user.username})" if current_user.is_authenticated else " (неавторизованный)"
    logger.info(f"Попытка добавления участника '{participant_name}' в турнир '{tournament.name}' (ID: {tournament_id}){user_info}")
    
    # Если передан user_id, используем его для поиска пользователя
    if 'user_id' in data and data['user_id']:
        user = User.query.get(data['user_id'])
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 400
        user_id = user.id
        participant_name = user.username
    else:
        # Используем переданное имя
        participant_name = data['name']
        
        # Проверяем дублирование по имени
        existing_name = Participant.query.filter_by(
            tournament_id=tournament_id, 
            name=participant_name
        ).first()
        
        if existing_name:
            return jsonify({'success': False, 'error': 'Участник с таким именем уже существует в этом турнире'}), 400
        
        # Если пользователь авторизован, проверяем дополнительные условия
        if current_user.is_authenticated:
            # Проверяем дублирование участника по user_id только для обычных участников
            if current_user.role not in ['администратор', 'доверенный_участник']:
                existing_participant = Participant.query.filter_by(
                    tournament_id=tournament_id,
                    user_id=current_user.id
                ).first()
                
                if existing_participant:
                    return jsonify({'success': False, 'error': 'Вы уже зарегистрированы на этот турнир'}), 400
            
            # Проверяем права для добавления других участников
            if current_user.role not in ['администратор', 'доверенный_участник']:
                # Обычный участник может добавить только себя
                if participant_name != current_user.username:
                    return jsonify({'success': False, 'error': 'Недостаточно прав для добавления других участников'}), 403
            
            # Для ручного ввода имен участников (не привязанных к пользователям)
            # Создаем участника без привязки к конкретному пользователю
            user_id = None
        else:
            # Для неавторизованных пользователей (кнопка "Хочу участвовать")
            # Ищем пользователя по имени
            user = User.query.filter_by(username=participant_name).first()
            if not user:
                return jsonify({'success': False, 'error': 'Пользователь не найден. Сначала зарегистрируйтесь.'}), 400
            user_id = user.id
    
    # Проверяем, не добавлен ли уже этот пользователь в турнир (только если user_id не None)
    if user_id is not None:
        existing_participant = Participant.query.filter_by(
            tournament_id=tournament_id,
            user_id=user_id
        ).first()
        
        if existing_participant:
            return jsonify({'success': False, 'error': f'Пользователь {participant_name} уже участвует в этом турнире'}), 400
    
    try:
        participant = Participant(
            tournament_id=tournament_id,
            user_id=user_id,
            name=participant_name,
            is_team=data.get('is_team', False)
        )
        db.session.add(participant)
        db.session.commit()
        
        # Создаем расписание матчей для нового участника
        create_schedule_for_participant(tournament_id, participant.id)
        
        logger.info(f"Успешное добавление участника '{participant_name}' в турнир '{tournament.name}' (Participant ID: {participant.id})")
        
        return jsonify({'success': True, 'participant_id': participant.id})
    except Exception as e:
        logger.error(f"Ошибка при добавлении участника '{participant_name}' в турнир '{tournament.name}': {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/register', methods=['POST'])
@login_required
def register_for_tournament(tournament_id):
    """Запись авторизованного пользователя на турнир"""
    tournament = Tournament.query.get_or_404(tournament_id)
    
    logger.info(f"Попытка записи пользователя '{current_user.username}' на турнир '{tournament.name}' (ID: {tournament_id})")
    
    # Проверяем, не участвует ли уже пользователь в турнире
    existing_participant = Participant.query.filter_by(
        tournament_id=tournament_id,
        user_id=current_user.id
    ).first()
    
    if existing_participant:
        logger.warning(f"Пользователь '{current_user.username}' уже участвует в турнире '{tournament.name}'")
        return jsonify({'success': False, 'error': 'Вы уже участвуете в этом турнире'}), 400
    
    try:
        participant = Participant(
            tournament_id=tournament_id,
            user_id=current_user.id,
            name=current_user.username,
            is_team=False
        )
        db.session.add(participant)
        db.session.commit()
        
        # Создаем расписание матчей для нового участника
        create_schedule_for_participant(tournament_id, participant.id)
        
        logger.info(f"Успешная запись пользователя '{current_user.username}' на турнир '{tournament.name}' (Participant ID: {participant.id})")
        
        return jsonify({'success': True, 'participant_id': participant.id})
    except Exception as e:
        logger.error(f"Ошибка при записи пользователя '{current_user.username}' на турнир '{tournament.name}': {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/register-and-participate', methods=['POST'])
def register_and_participate(tournament_id):
    """Полный процесс: регистрация пользователя + авторизация + запись на турнир"""
    logger.info(f"ПОЛУЧЕН ЗАПРОС на /api/tournaments/{tournament_id}/register-and-participate")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {dict(request.headers)}")
    logger.info(f"Request data: {request.get_data()}")
    
    tournament = Tournament.query.get_or_404(tournament_id)
    data = request.get_json()
    
    logger.info(f"Parsed JSON data: {data}")
    
    username = data.get('username', 'неизвестно') if data else 'неизвестно'
    password = data.get('password', '') if data else ''
    
    logger.info(f"Начало процесса регистрации и записи на турнир: пользователь '{username}', турнир '{tournament.name}' (ID: {tournament_id})")
    
    # Проверяем, не существует ли уже пользователь с таким именем
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        logger.warning(f"Попытка регистрации существующего пользователя '{username}' для участия в турнире")
        return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует'}), 400
    
    try:
        # Создаем нового пользователя
        user = User(
            username=username,
            password_hash=password,  # В реальном приложении пароль нужно хешировать
            role='участник'
        )
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"Успешная регистрация пользователя '{username}' (ID: {user.id}) для участия в турнире")
        
        # Автоматически входим в систему
        login_user(user)
        logger.info(f"Автоматический вход пользователя '{username}' после регистрации")
        
        # Проверяем, не участвует ли уже пользователь в турнире
        existing_participant = Participant.query.filter_by(
            tournament_id=tournament_id,
            user_id=user.id
        ).first()
        
        if existing_participant:
            logger.warning(f"Пользователь '{username}' уже участвует в турнире '{tournament.name}'")
            return jsonify({'success': False, 'error': 'Вы уже участвуете в этом турнире'}), 400
        
        # Добавляем пользователя в турнир
        participant = Participant(
            tournament_id=tournament_id,
            user_id=user.id,
            name=username,
            is_team=False
        )
        db.session.add(participant)
        db.session.commit()
        
        # Создаем расписание матчей для нового участника
        create_schedule_for_participant(tournament_id, participant.id)
        
        logger.info(f"Успешная запись пользователя '{username}' на турнир '{tournament.name}' (Participant ID: {participant.id})")
        logger.info(f"Полный процесс завершен: регистрация + авторизация + запись на турнир для пользователя '{username}'")
        
        return jsonify({
            'success': True, 
            'message': 'Вы успешно зарегистрированы, авторизованы и добавлены в турнир!',
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            },
            'participant_id': participant.id
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Ошибка в процессе регистрации и записи на турнир для пользователя '{username}': {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>', methods=['DELETE'])
@login_required
def delete_tournament(tournament_id):
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для удаления турнира'}), 403
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    try:
        # Удаляем все связанные данные
        Match.query.filter_by(tournament_id=tournament_id).delete()
        Participant.query.filter_by(tournament_id=tournament_id).delete()
        db.session.delete(tournament)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Турнир удален'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/participants/<int:participant_id>', methods=['DELETE'])
@login_required
def delete_participant(tournament_id, participant_id):
    if current_user.role not in ['администратор', 'доверенный_участник']:
        logger.warning(f"Попытка удаления участника без прав пользователем: {current_user.username}")
        return jsonify({'success': False, 'error': 'Недостаточно прав для удаления участника'}), 403
    
    participant = Participant.query.filter_by(
        tournament_id=tournament_id, 
        id=participant_id
    ).first_or_404()
    
    logger.info(f"Попытка удаления участника '{participant.name}' из турнира ID: {tournament_id} пользователем: {current_user.username}")
    
    try:
        # Удаляем все матчи с этим участником
        Match.query.filter(
            (Match.participant1_id == participant_id) | (Match.participant2_id == participant_id),
            Match.tournament_id == tournament_id
        ).delete()
        
        # Удаляем участника
        db.session.delete(participant)
        db.session.commit()
        
        logger.info(f"Успешное удаление участника '{participant.name}' из турнира ID: {tournament_id}")
        
        return jsonify({'success': True, 'message': 'Участник удален'})
    except Exception as e:
        logger.error(f"Ошибка при удалении участника '{participant.name}': {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/reschedule', methods=['POST'])
@login_required
def reschedule_tournament(tournament_id):
    """Пересчет расписания турнира для устранения конфликтов"""
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для пересчета расписания'}), 403
    
    tournament = Tournament.query.get_or_404(tournament_id)
    
    try:
        # Получаем всех участников турнира
        participants = Participant.query.filter_by(tournament_id=tournament_id).all()
        
        # Удаляем все существующие матчи
        Match.query.filter_by(tournament_id=tournament_id).delete()
        db.session.commit()
        
        # Создаем новое расписание
        for i, p1 in enumerate(participants):
            for j, p2 in enumerate(participants):
                if i < j:  # Избегаем дублирования матчей
                    match_time = calculate_match_time(tournament, p1.id, p2.id)
                    
                    match = Match(
                        tournament_id=tournament_id,
                        participant1_id=p1.id,
                        participant2_id=p2.id,
                        match_date=match_time['date'],
                        match_time=match_time['time'],
                        court_number=match_time['court'],
                        status='запланирован'
                    )
                    db.session.add(match)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Расписание пересчитано'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/matches/<int:match_id>', methods=['DELETE'])
@login_required
def delete_match(match_id):
    if current_user.role not in ['администратор', 'доверенный_участник']:
        return jsonify({'success': False, 'error': 'Недостаточно прав для удаления матча'}), 403
    
    match = Match.query.get_or_404(match_id)
    
    try:
        # Удаляем матч
        db.session.delete(match)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Матч удален'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def create_schedule_for_participant(tournament_id, participant_id):
    """Создание расписания матчей для нового участника"""
    tournament = Tournament.query.get(tournament_id)
    participants = Participant.query.filter_by(tournament_id=tournament_id).all()
    
    if len(participants) < 2:
        return
    
    # Получаем существующие матчи
    existing_matches = Match.query.filter_by(tournament_id=tournament_id).all()
    
    # Создаем матчи с новым участником
    for other_participant in participants:
        if other_participant.id != participant_id:
            # Проверяем, не существует ли уже матч
            match_exists = any(
                (m.participant1_id == participant_id and m.participant2_id == other_participant.id) or
                (m.participant1_id == other_participant.id and m.participant2_id == participant_id)
                for m in existing_matches
            )
            
            if not match_exists:
                # Определяем время матча с учетом нагрузки
                match_time = calculate_match_time(tournament, participant_id, other_participant.id)
                
                match = Match(
                    tournament_id=tournament_id,
                    participant1_id=participant_id,
                    participant2_id=other_participant.id,
                    match_date=match_time['date'],
                    match_time=match_time['time'],
                    court_number=match_time['court'],
                    status='запланирован'
                )
                db.session.add(match)
    
    db.session.commit()

def calculate_match_time(tournament, p1_id, p2_id):
    """Расчет времени матча с учетом нагрузки участников и площадок"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Начинаем с первой даты турнира
    current_date = tournament.start_date
    current_time = datetime.strptime('09:00', '%H:%M').time()  # Начало в 9:00
    
    # Ищем свободное время
    while current_date <= tournament.end_date:
        # Проверяем все временные слоты в течение дня
        while current_time < datetime.strptime('22:00', '%H:%M').time():
            # Проверяем все площадки для этого времени
            for court in range(1, tournament.court_count + 1):
                # Проверяем, свободна ли площадка в это время
                if is_court_available(tournament, current_date, current_time, court):
                    # Проверяем, не играет ли участник в это время
                    if not is_participant_busy(tournament, p1_id, current_date, current_time) and \
                       not is_participant_busy(tournament, p2_id, current_date, current_time):
                        
                        # Дополнительная проверка: не играл ли участник в предыдущем временном слоте
                        if not is_participant_recently_played(tournament, p1_id, current_date, current_time) and \
                           not is_participant_recently_played(tournament, p2_id, current_date, current_time):
                            
                            # Дополнительная проверка: не играет ли участник в следующем временном слоте
                            next_time = add_minutes_to_time(current_time, tournament.match_duration + tournament.break_duration)
                            if next_time < datetime.strptime('22:00', '%H:%M').time():
                                if not is_participant_busy(tournament, p1_id, current_date, next_time) and \
                                   not is_participant_busy(tournament, p2_id, current_date, next_time):
                                    return {
                                        'date': current_date,
                                        'time': current_time,
                                        'court': court
                                    }
                            else:
                                return {
                                    'date': current_date,
                                    'time': current_time,
                                    'court': court
                                }
            
            # Переходим к следующему времени
            current_time = add_minutes_to_time(current_time, tournament.match_duration + tournament.break_duration)
        
        # Переходим к следующему дню
        current_date += timedelta(days=1)
        current_time = datetime.strptime('09:00', '%H:%M').time()
    
    # Если не нашли время, возвращаем последний день
    return {
        'date': tournament.end_date,
        'time': datetime.strptime('09:00', '%H:%M').time(),
        'court': 1
    }

def is_court_available(tournament, date, time, court):
    """Проверка доступности площадки"""
    matches = Match.query.filter_by(
        tournament_id=tournament.id,
        court_number=court,
        match_date=date
    ).all()
    
    check_datetime = datetime.combine(date, time)
    
    for match in matches:
        if match.match_time:
            match_start = datetime.combine(date, match.match_time)
            match_end = match_start + timedelta(minutes=tournament.match_duration)
            
            # Площадка занята, если проверяемое время попадает в интервал матча
            if match_start <= check_datetime < match_end:
                return False
    
    return True

def is_participant_busy(tournament, participant_id, date, time):
    """Проверка занятости участника"""
    matches = Match.query.filter(
        (Match.participant1_id == participant_id) | (Match.participant2_id == participant_id),
        Match.tournament_id == tournament.id,
        Match.match_date == date
    ).all()
    
    check_datetime = datetime.combine(date, time)
    
    for match in matches:
        if match.match_time:
            match_start = datetime.combine(date, match.match_time)
            match_end = match_start + timedelta(minutes=tournament.match_duration)
            
            # Проверяем, не пересекается ли время матча с проверяемым временем
            # Участник занят, если проверяемое время попадает в интервал матча
            if match_start <= check_datetime < match_end:
                return True
    
    return False

def add_minutes_to_time(time, minutes):
    """Добавление минут к времени"""
    dt = datetime.combine(datetime.today(), time)
    new_dt = dt + timedelta(minutes=minutes)
    return new_dt.time()

def is_participant_recently_played(tournament, participant_id, date, time):
    """Проверка, не играл ли участник недавно (в предыдущем временном слоте)"""
    # Рассчитываем время предыдущего временного слота
    prev_time = add_minutes_to_time(time, -(tournament.match_duration + tournament.break_duration))
    
    # Если предыдущее время меньше 9:00, проверяем предыдущий день
    if prev_time < datetime.strptime('09:00', '%H:%M').time():
        prev_date = date - timedelta(days=1)
        # Исправляем проблему с datetime.time
        end_time = datetime.strptime('22:00', '%H:%M').time()
        end_dt = datetime.combine(prev_date, end_time)
        prev_dt = end_dt - timedelta(minutes=tournament.match_duration + tournament.break_duration)
        prev_time = prev_dt.time()
    else:
        prev_date = date
    
    # Проверяем, играл ли участник в предыдущем временном слоте
    matches = Match.query.filter(
        (Match.participant1_id == participant_id) | (Match.participant2_id == participant_id),
        Match.tournament_id == tournament.id,
        Match.match_date == prev_date
    ).all()
    
    for match in matches:
        if match.match_time:
            # Проверяем, играл ли участник в предыдущем временном слоте
            match_datetime = datetime.combine(prev_date, match.match_time)
            prev_datetime = datetime.combine(prev_date, prev_time)
            
            # Проверяем, что матч был в предыдущем временном слоте
            if abs((match_datetime - prev_datetime).total_seconds()) < 300:  # 5 минут погрешности
                return True
    
    return False

@app.route('/api/matches', methods=['POST'])
@login_required
def create_match():
    if current_user.role not in ['администратор', 'доверенный_участник']:
        return jsonify({'error': 'Недостаточно прав'}), 403
    
    data = request.get_json()
    
    try:
        match = Match(
            tournament_id=data['tournament_id'],
            participant1_id=data['participant1_id'],
            participant2_id=data['participant2_id'],
            score1=data.get('score1'),
            score2=data.get('score2'),
            match_date=datetime.strptime(data['match_date'], '%Y-%m-%d').date() if data.get('match_date') else None,
            match_time=datetime.strptime(data['match_time'], '%H:%M').time() if data.get('match_time') else None,
            court_number=data.get('court_number'),
            status='завершен' if data.get('score1') and data.get('score2') else 'запланирован'
        )
        
        # Обновляем победителя если есть счет
        if match.score1 is not None and match.score2 is not None:
            match.winner_id = match.participant1_id if match.score1 > match.score2 else match.participant2_id
        
        db.session.add(match)
        db.session.commit()
        
        # Логируем создание матча
        if match.score1 and match.score2:
            log = MatchLog(
                match_id=match.id,
                user_id=current_user.id,
                action='создан',
                new_score1=match.score1,
                new_score2=match.score2
            )
            db.session.add(log)
            db.session.commit()
        
        return jsonify({'success': True, 'match_id': match.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/matches/<int:match_id>', methods=['PUT'])
@login_required
def update_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    # Проверяем права на редактирование
    if current_user.role not in ['администратор', 'доверенный_участник']:
        # Участник может редактировать только свои матчи
        if current_user.id not in [match.participant1.user_id, match.participant2.user_id]:
            return jsonify({'error': 'Недостаточно прав'}), 403
    
    data = request.get_json()
    
    try:
        # Сохраняем старые значения для лога
        old_score1 = match.score1
        old_score2 = match.score2
        
        # Обновляем матч
        if 'score1' in data:
            match.score1 = data['score1']
        if 'score2' in data:
            match.score2 = data['score2']
        if 'match_date' in data and data['match_date']:
            match.match_date = datetime.strptime(data['match_date'], '%Y-%m-%d').date()
        if 'match_time' in data and data['match_time']:
            match.match_time = datetime.strptime(data['match_time'], '%H:%M').time()
        if 'court_number' in data:
            match.court_number = data['court_number']
        
        # Обновляем статус и победителя
        if match.score1 is not None and match.score2 is not None:
            match.status = 'завершен'
            match.winner_id = match.participant1_id if match.score1 > match.score2 else match.participant2_id
        else:
            match.status = 'запланирован'
            match.winner_id = None
        
        match.updated_at = datetime.utcnow()
        
        # Логируем изменение
        if old_score1 != match.score1 or old_score2 != match.score2:
            log = MatchLog(
                match_id=match.id,
                user_id=current_user.id,
                action='изменен',
                old_score1=old_score1,
                old_score2=old_score2,
                new_score1=match.score1,
                new_score2=match.score2
            )
            db.session.add(log)
        
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/matches/<int:match_id>', methods=['GET'])
@login_required
def get_match(match_id):
    match = Match.query.get_or_404(match_id)
    
    return jsonify({
        'success': True,
        'match': {
            'id': match.id,
            'participant1_id': match.participant1_id,
            'participant2_id': match.participant2_id,
            'score1': match.score1,
            'score2': match.score2,
            'match_date': match.match_date.strftime('%Y-%m-%d') if match.match_date else None,
            'match_time': match.match_time.strftime('%H:%M') if match.match_time else None,
            'court_number': match.court_number,
            'status': match.status
        }
    })

@app.route('/tournament/<int:tournament_id>')
def tournament_view(tournament_id):
    tournament = Tournament.query.get_or_404(tournament_id)
    participants = Participant.query.filter_by(tournament_id=tournament_id).all()
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
    
    # Создание шахматки и статистики
    chessboard = create_chessboard(participants, matches)
    statistics = calculate_statistics(participants, matches, tournament)
    
    # Преобразуем участников в словари для JSON сериализации
    participants_data = []
    for participant in participants:
        participants_data.append({
            'id': participant.id,
            'name': participant.name,
            'is_team': participant.is_team,
            'user_id': participant.user_id
        })
    
    # Преобразуем матчи в словари для JSON сериализации
    matches_data = []
    for match in matches:
        matches_data.append({
            'id': match.id,
            'participant1_id': match.participant1_id,
            'participant2_id': match.participant2_id,
            'score1': match.score1,
            'score2': match.score2,
            'match_date': match.match_date.strftime('%Y-%m-%d') if match.match_date else None,
            'match_time': match.match_time.strftime('%H:%M') if match.match_time else None,
            'court_number': match.court_number,
            'status': match.status
        })
    
    return render_template('tournament.html', 
                         tournament=tournament, 
                         participants=participants, 
                         participants_data=participants_data,
                         matches=matches,
                         matches_data=matches_data,
                         chessboard=chessboard,
                         statistics=statistics)

def create_chessboard(participants, matches):
    """Создание шахматки для отображения результатов"""
    chessboard = {}
    
    # Находим две ближайшие игры для выделения
    now = datetime.now()
    upcoming_matches = [m for m in matches if m.status != 'завершен' and m.match_date and m.match_time]
    
    next_matches = []
    if upcoming_matches:
        # Сортируем по дате и времени
        upcoming_matches.sort(key=lambda m: (m.match_date, m.match_time))
        # Берем две ближайшие игры
        next_matches = upcoming_matches[:2]
    
    for p1 in participants:
        chessboard[p1.id] = {}
        for p2 in participants:
            if p1.id == p2.id:
                chessboard[p1.id][p2.id] = {'type': 'diagonal', 'value': '—'}
            else:
                # Поиск матча между участниками
                match = next((m for m in matches 
                            if (m.participant1_id == p1.id and m.participant2_id == p2.id) or
                               (m.participant1_id == p2.id and m.participant2_id == p1.id)), None)
                
                if match:
                    if match.status == 'завершен':
                        if match.participant1_id == p1.id:
                            score = f"{match.score1}:{match.score2}"
                        else:
                            score = f"{match.score2}:{match.score1}"
                        chessboard[p1.id][p2.id] = {
                            'type': 'result',
                            'value': score,
                            'match_id': match.id,
                            'editable': True
                        }
                    else:
                        # Следующая игра
                        match_datetime = datetime.combine(match.match_date, match.match_time)
                        
                        # Определяем позицию в очереди ближайших игр
                        match_position = None
                        for i, next_match in enumerate(next_matches):
                            next_match_datetime = datetime.combine(next_match.match_date, next_match.match_time)
                            if match_datetime == next_match_datetime:
                                match_position = i + 1  # 1 - первая игра, 2 - вторая игра
                                break
                        
                        chessboard[p1.id][p2.id] = {
                            'type': 'upcoming',
                            'value': f"📅 {match.match_date.strftime('%d.%m')} {match.match_time.strftime('%H:%M')}",
                            'match_id': match.id,
                            'editable': False,
                            'date': match.match_date,
                            'time': match.match_time,
                            'court': match.court_number,
                            'is_next': match_position == 1,  # Флаг для выделения первой ближайшей игры
                            'is_second': match_position == 2  # Флаг для выделения второй ближайшей игры
                        }
                else:
                    chessboard[p1.id][p2.id] = {'type': 'empty', 'value': ''}
    
    return chessboard

def calculate_statistics(participants, matches, tournament):
    """Расчет статистики участников"""
    stats = {}
    for participant in participants:
        stats[participant.id] = {
            'games': 0,
            'wins': 0,
            'losses': 0,
            'draws': 0,
            'points': 0,
            'goal_difference': 0
        }
    
    for match in matches:
        if match.status == 'завершен' and match.score1 is not None and match.score2 is not None:
            p1_id = match.participant1_id
            p2_id = match.participant2_id
            
            # Обновляем статистику
            stats[p1_id]['games'] += 1
            stats[p2_id]['games'] += 1
            
            if match.score1 > match.score2:
                stats[p1_id]['wins'] += 1
                stats[p2_id]['losses'] += 1
                stats[p1_id]['points'] += tournament.points_win
                stats[p2_id]['points'] += tournament.points_loss
            elif match.score1 < match.score2:
                stats[p2_id]['wins'] += 1
                stats[p1_id]['losses'] += 1
                stats[p2_id]['points'] += tournament.points_win
                stats[p1_id]['points'] += tournament.points_loss
            else:
                # Ничья
                stats[p1_id]['draws'] += 1
                stats[p2_id]['draws'] += 1
                stats[p1_id]['points'] += tournament.points_draw
                stats[p2_id]['points'] += tournament.points_draw
            
            stats[p1_id]['goal_difference'] += match.score1 - match.score2
            stats[p2_id]['goal_difference'] += match.score2 - match.score1
    
    return stats

if __name__ == '__main__':
    app.run(debug=True)
