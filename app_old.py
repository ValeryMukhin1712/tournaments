from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import logging
import secrets

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
        logging.FileHandler('tournament.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Импорт моделей из модулей
from models import create_models

# Создание моделей с текущим экземпляром db
models = create_models(db)
User = models['User']
Tournament = models['Tournament']
Participant = models['Participant']
Match = models['Match']
Notification = models['Notification']
MatchLog = models['MatchLog']

# Импорт и регистрация маршрутов
from routes import register_routes
register_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создание таблиц
with app.app_context():
    db.create_all()
    
    # Создание администратора по умолчанию
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', password_hash=generate_password_hash('admin123'), role='администратор')
        db.session.add(admin)
        db.session.commit()

# Маршруты перенесены в routes/main.py

# Маршруты аутентификации перенесены в routes/auth.py

# Все API маршруты перенесены в routes/api.py

# Вспомогательные функции перенесены в соответствующие модули

def create_chessboard_data(tournament, participants, matches):
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
            password_hash=generate_password_hash(data['password']),  # Безопасное хеширование пароля
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
            password_hash=generate_password_hash(password),  # Безопасное хеширование пароля
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
    """Пересчет расписания турнира по методу Round-robin"""
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для пересчета расписания'}), 403

    try:
        success = create_round_robin_schedule(tournament_id)

        if success:
            return jsonify({'success': True, 'message': 'Расписание пересчитано по методу Round-robin'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка при создании расписания'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/create-missing-matches', methods=['POST'])
@login_required
def create_missing_matches(tournament_id):
    """Создание всех недостающих матчей для турнира"""
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для создания матчей'}), 403

    try:
        success = check_and_create_missing_matches(tournament_id)

        if success:
            return jsonify({'success': True, 'message': 'Недостающие матчи созданы'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка при создании матчей'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/tournaments/<int:tournament_id>/debug-chessboard', methods=['POST'])
@login_required
def debug_chessboard(tournament_id):
    """Создание отладочного файла для турнирной таблицы"""
    if current_user.role != 'администратор':
        return jsonify({'success': False, 'error': 'Недостаточно прав для отладки'}), 403

    try:
        tournament = Tournament.query.get_or_404(tournament_id)
        participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        success = debug_chessboard_to_file(participants, matches, tournament_id)
        
        if success:
            return jsonify({'success': True, 'message': f'Отладочный файл создан: debug_chessboard_{tournament_id}.txt'})
        else:
            return jsonify({'success': False, 'error': 'Ошибка при создании отладочного файла'})
    except Exception as e:
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

def get_next_match_number(tournament_id):
    """Получение следующего номера матча для турнира"""
    last_match = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_number.desc()).first()
    if last_match and last_match.match_number:
        return last_match.match_number + 1
    return 1

def renumber_matches_chronologically(tournament_id):
    """Пересчет номеров матчей в хронологическом порядке"""
    all_matches = Match.query.filter_by(tournament_id=tournament_id).order_by(
        Match.match_date, Match.match_time, Match.court_number
    ).all()
    
    for match_number, match in enumerate(all_matches, 1):
        match.match_number = match_number
    
    db.session.commit()

def create_schedule_for_participant(tournament_id, participant_id):
    """Создание расписания матчей для нового участника"""
    # Используем автоматическую проверку и создание недостающих матчей
    check_and_create_missing_matches(tournament_id)

def calculate_match_time_new(tournament, p1_id, p2_id):
    """Алгоритм Round-robin для равномерного распределения матчей"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Ищем первый подходящий слот
    for date, time in time_slots:
        # Проверяем, не играют ли участники в это время
        p1_busy = any(
            m.match_date == date and m.match_time == time and 
            (m.participant1_id == p1_id or m.participant2_id == p1_id)
            for m in matches
        )
        p2_busy = any(
            m.match_date == date and m.match_time == time and 
            (m.participant1_id == p2_id or m.participant2_id == p2_id)
            for m in matches
        )
        
        if p1_busy or p2_busy:
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            court_busy = any(
                m.match_date == date and m.match_time == time and m.court_number == court
                for m in matches
            )
            if not court_busy:
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback - если не нашли свободный слот, берем последний
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def check_and_create_missing_matches(tournament_id):
    """Проверка и автоматическое создание недостающих матчей"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return False
    
    # Получаем всех участников
    participants = Participant.query.filter_by(tournament_id=tournament_id).all()
    n = len(participants)
    if n < 2:
        return False
    
    # Вычисляем необходимое количество матчей для кругового турнира
    required_matches = n * (n - 1) // 2
    
    # Получаем количество существующих матчей
    existing_matches_count = Match.query.filter_by(tournament_id=tournament_id).count()
    
    logger.info(f"Турнир {tournament_id}: участников={n}, требуется матчей={required_matches}, существует={existing_matches_count}")
    
    # Если матчей недостаточно, создаем недостающие
    if existing_matches_count < required_matches:
        logger.info(f"Создаем недостающие матчи: {required_matches - existing_matches_count}")
        return create_all_missing_matches(tournament_id)
    
    return True

def has_missing_matches(tournament_id):
    """Проверка, есть ли недостающие матчи в турнире"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return False
    
    # Получаем всех участников
    participants = Participant.query.filter_by(tournament_id=tournament_id).all()
    n = len(participants)
    if n < 2:
        return False
    
    # Вычисляем необходимое количество матчей для кругового турнира
    required_matches = n * (n - 1) // 2
    
    # Получаем количество существующих матчей
    existing_matches_count = Match.query.filter_by(tournament_id=tournament_id).count()
    
    return existing_matches_count < required_matches

def create_all_missing_matches(tournament_id):
    """Создание всех недостающих матчей для турнира"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return False
    
    # Получаем всех участников
    participants = Participant.query.filter_by(tournament_id=tournament_id).all()
    if len(participants) < 2:
        return False
    
    # Получаем существующие матчи
    existing_matches = Match.query.filter_by(tournament_id=tournament_id).all()
    
    # Создаем все возможные пары участников
    matches_created = 0
    for i, p1 in enumerate(participants):
        for j, p2 in enumerate(participants):
            if i < j:  # Избегаем дублирования (1vs2 и 2vs1)
                # Проверяем, не существует ли уже матч
                match_exists = any(
                    (m.participant1_id == p1.id and m.participant2_id == p2.id) or
                    (m.participant1_id == p2.id and m.participant2_id == p1.id)
                    for m in existing_matches
                )
                
                if not match_exists:
                    # Определяем время матча
                    match_time = calculate_match_time_new(tournament, p1.id, p2.id)
                    
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
                    matches_created += 1
                    logger.info(f"Создан матч: {p1.name} vs {p2.name}")
    
    db.session.commit()
    
    # Пересчитываем номера матчей в хронологическом порядке
    renumber_matches_chronologically(tournament_id)
    
    logger.info(f"Создано {matches_created} новых матчей для турнира {tournament_id}")
    return matches_created > 0

def create_round_robin_schedule(tournament_id):
    """Создание расписания по методу круговой таблицы (Round-robin)"""
    tournament = Tournament.query.get(tournament_id)
    if not tournament:
        return False
    
    # Получаем всех участников
    participants = Participant.query.filter_by(tournament_id=tournament_id).all()
    if len(participants) < 2:
        return False
    
    # Удаляем существующие матчи
    Match.query.filter_by(tournament_id=tournament_id).delete()
    db.session.commit()
    
    # Создаем список ID участников
    participant_ids = [p.id for p in participants]
    n = len(participant_ids)
    
    # Если нечетное количество участников, добавляем "bye" (пропуск)
    if n % 2 == 1:
        participant_ids.append(None)  # None означает "bye"
        n += 1
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    slot_index = 0
    
    # Round-robin алгоритм
    for round_num in range(n - 1):
        # Создаем пары для текущего раунда
        for i in range(n // 2):
            p1_id = participant_ids[i]
            p2_id = participant_ids[n - 1 - i]
            
            # Пропускаем "bye"
            if p1_id is None or p2_id is None:
                continue
            
            # Находим свободный временной слот
            while slot_index < len(time_slots):
                date, time = time_slots[slot_index]
                
                # Проверяем, не заняты ли участники в это время
                p1_busy = Match.query.filter_by(
                    tournament_id=tournament_id
                ).filter(
                    (Match.participant1_id == p1_id) | (Match.participant2_id == p1_id),
                    Match.match_date == date,
                    Match.match_time == time
                ).first()
                
                p2_busy = Match.query.filter_by(
                    tournament_id=tournament_id
                ).filter(
                    (Match.participant1_id == p2_id) | (Match.participant2_id == p2_id),
                    Match.match_date == date,
                    Match.match_time == time
                ).first()
                
                if not p1_busy and not p2_busy:
                    # Находим свободную площадку
                    for court in range(1, tournament.court_count + 1):
                        court_busy = Match.query.filter_by(
                            tournament_id=tournament_id,
                            match_date=date,
                            match_time=time,
                            court_number=court
                        ).first()
                        
                        if not court_busy:
                            # Создаем матч
                            match = Match(
                                tournament_id=tournament_id,
                                participant1_id=p1_id,
                                participant2_id=p2_id,
                                match_date=date,
                                match_time=time,
                                court_number=court,
                                status='запланирован'
                            )
                            db.session.add(match)
                            break
                    break
                slot_index += 1
        
        # Поворачиваем участников (кроме первого)
        if n > 2:
            participant_ids = [participant_ids[0]] + [participant_ids[-1]] + participant_ids[1:-1]
    
    db.session.commit()
    
    # Пересчитываем номера матчей в хронологическом порядке
    renumber_matches_chronologically(tournament_id)
    
    return True

def calculate_match_time_simple(tournament, p1_id, p2_id):
    """Простой алгоритм расчета времени матча с равномерной загрузкой"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_round_robin(tournament, p1_id, p2_id):
    """Алгоритм Round Robin для равномерного распределения матчей"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_balanced(tournament, p1_id, p2_id):
    """Расчет времени матча с учетом равномерной загрузки участников"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_sequential(tournament, p1_id, p2_id):
    """Последовательный алгоритм расчета времени матча"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_fixed(tournament, p1_id, p2_id):
    """Фиксированный алгоритм расчета времени матча с учетом уже запланированных матчей"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_round_robin(tournament, p1_id, p2_id):
    """Алгоритм Round Robin для равномерного распределения матчей"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_round_robin(tournament, p1_id, p2_id):
    """Алгоритм Round Robin для равномерного распределения матчей"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_round_robin(tournament, p1_id, p2_id):
    """Алгоритм Round Robin для равномерного распределения матчей"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем слоты по приоритету (участники с меньшей нагрузкой получают приоритет)
    def get_slot_priority(date, time):
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        return p1_load + p2_load
    
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играл ли участник недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Ищем свободную площадку
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Если не нашли идеальный слот, ищем любой доступный
    for date, time in time_slots:
        has_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                return {'date': date, 'time': time, 'court': court}
    
    # Fallback
    if time_slots:
        last_slot = time_slots[-1]
        return {'date': last_slot[0], 'time': last_slot[1], 'court': 1}
    
    return {'date': tournament.start_date, 'time': datetime.strptime('09:00', '%H:%M').time(), 'court': 1}

def calculate_match_time_balanced(tournament, p1_id, p2_id):
    """Расчет времени матча с учетом равномерной загрузки участников"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Подсчитываем загрузку каждого участника
    participant_load = {}
    for match in matches:
        if match.participant1_id not in participant_load:
            participant_load[match.participant1_id] = 0
        if match.participant2_id not in participant_load:
            participant_load[match.participant2_id] = 0
        participant_load[match.participant1_id] += 1
        participant_load[match.participant2_id] += 1
    
    # Инициализируем загрузку для новых участников
    if p1_id not in participant_load:
        participant_load[p1_id] = 0
    if p2_id not in participant_load:
        participant_load[p2_id] = 0
    
    # Создаем карту загрузки площадок
    court_usage = {}
    for court in range(1, tournament.court_count + 1):
        court_usage[court] = 0
    
    # Подсчитываем текущую загрузку площадок
    for match in matches:
        if match.court_number and match.court_number in court_usage:
            court_usage[match.court_number] += 1
    
    # Генерируем все возможные временные слоты
    time_slots = []
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем временные слоты по приоритету
    def get_slot_priority(date, time):
        # Приоритет = загрузка участников + загрузка площадок
        p1_load = participant_load.get(p1_id, 0)
        p2_load = participant_load.get(p2_id, 0)
        participant_priority = p1_load + p2_load
        
        # Подсчитываем загрузку площадок в это время
        court_load = 0
        for court in range(1, tournament.court_count + 1):
            if not is_court_available(tournament, date, time, court):
                court_load += 1
        
        return participant_priority * 100 + court_load  # Участники важнее площадок
    
    # Сортируем слоты по приоритету (меньше загрузка = выше приоритет)
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий временной слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, conflict_message = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играли ли участники недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Дополнительная проверка: не играют ли участники в соседних временных слотах
        slot_duration = tournament.match_duration + tournament.break_duration
        
        # Проверяем предыдущий слот
        prev_time = add_minutes_to_time(time, -slot_duration)
        if prev_time >= datetime.strptime('09:00', '%H:%M').time():
            if has_participant_match_at_time(tournament, p1_id, date, prev_time) or \
               has_participant_match_at_time(tournament, p2_id, date, prev_time):
                continue
        
        # Проверяем следующий слот
        next_time = add_minutes_to_time(time, slot_duration)
        if next_time <= datetime.strptime('22:00', '%H:%M').time():
            if has_participant_match_at_time(tournament, p1_id, date, next_time) or \
               has_participant_match_at_time(tournament, p2_id, date, next_time):
                continue
        
        # Находим наименее загруженную площадку в это время
        best_court = None
        min_usage = float('inf')
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                current_usage = court_usage[court]
                if current_usage < min_usage:
                    min_usage = current_usage
                    best_court = court
        
        if best_court:
            return {
                'date': date,
                'time': time,
                'court': best_court
            }
    
    # Если не нашли подходящее время с полными ограничениями, 
    # попробуем найти время с ослабленными ограничениями
    for date, time in time_slots:
        # Проверяем только основные конфликты (участники не играют одновременно)
        has_conflict, conflict_message = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Находим наименее загруженную площадку в это время
        best_court = None
        min_usage = float('inf')
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                current_usage = court_usage[court]
                if current_usage < min_usage:
                    min_usage = current_usage
                    best_court = court
        
        if best_court:
            return {
                'date': date,
                'time': time,
                'court': best_court
            }
    
    # Если все еще не нашли, используем последний доступный слот
    # но стараемся избежать последовательных игр
    last_slot = time_slots[-1] if time_slots else (tournament.end_date, datetime.strptime('09:00', '%H:%M').time())
    
    # Проверяем, не играют ли участники в предыдущем слоте
    date, time = last_slot
    slot_duration = tournament.match_duration + tournament.break_duration
    prev_time = add_minutes_to_time(time, -slot_duration)
    
    # Если предыдущий слот в том же дне, проверяем его
    if prev_time >= datetime.strptime('09:00', '%H:%M').time():
        if has_participant_match_at_time(tournament, p1_id, date, prev_time) or \
           has_participant_match_at_time(tournament, p2_id, date, prev_time):
            # Если есть конфликт, ищем альтернативное время
            for alt_date, alt_time in reversed(time_slots[:-1]):
                if not has_participant_match_at_time(tournament, p1_id, alt_date, alt_time) and \
                   not has_participant_match_at_time(tournament, p2_id, alt_date, alt_time):
                    return {
                        'date': alt_date,
                        'time': alt_time,
                        'court': 1
                    }
    
    return {
        'date': date,
        'time': time,
        'court': 1
    }

def calculate_match_time(tournament, p1_id, p2_id):
    """Расчет времени матча с учетом равномерной загрузки площадок и проверки конфликтов участников"""
    # Получаем все матчи турнира
    matches = Match.query.filter_by(tournament_id=tournament.id).all()
    
    # Создаем карту загрузки площадок для равномерного распределения
    court_usage = {}
    for court in range(1, tournament.court_count + 1):
        court_usage[court] = 0
    
    # Подсчитываем текущую загрузку площадок
    for match in matches:
        if match.court_number and match.court_number in court_usage:
            court_usage[match.court_number] += 1
    
    # Начинаем с первой даты турнира
    current_date = tournament.start_date
    current_time = datetime.strptime('09:00', '%H:%M').time()  # Начало в 9:00
    
    # Список всех возможных временных слотов для сортировки по приоритету
    time_slots = []
    
    # Генерируем все возможные временные слоты
    temp_date = tournament.start_date
    while temp_date <= tournament.end_date:
        temp_time = datetime.strptime('09:00', '%H:%M').time()
        while temp_time < datetime.strptime('22:00', '%H:%M').time():
            time_slots.append((temp_date, temp_time))
            temp_time = add_minutes_to_time(temp_time, tournament.match_duration + tournament.break_duration)
        temp_date += timedelta(days=1)
    
    # Сортируем временные слоты по приоритету (сначала менее загруженные площадки)
    def get_slot_priority(date, time):
        # Подсчитываем загрузку всех площадок в это время
        total_load = 0
        for court in range(1, tournament.court_count + 1):
            if not is_court_available(tournament, date, time, court):
                total_load += 1
        return total_load
    
    # Сортируем слоты по приоритету (меньше загрузка = выше приоритет)
    time_slots.sort(key=lambda slot: get_slot_priority(slot[0], slot[1]))
    
    # Ищем подходящий временной слот
    for date, time in time_slots:
        # Проверяем конфликты участников
        has_conflict, conflict_message = check_participant_conflicts(tournament, p1_id, p2_id, date, time)
        if has_conflict:
            continue
        
        # Проверяем, не играли ли участники недавно
        if is_participant_recently_played(tournament, p1_id, date, time) or \
           is_participant_recently_played(tournament, p2_id, date, time):
            continue
        
        # Проверяем, не играют ли участники в следующем временном слоте
        next_time = add_minutes_to_time(time, tournament.match_duration + tournament.break_duration)
        if next_time < datetime.strptime('22:00', '%H:%M').time():
            has_next_conflict, _ = check_participant_conflicts(tournament, p1_id, p2_id, date, next_time)
            if has_next_conflict:
                continue
        
        # Находим наименее загруженную площадку в это время
        best_court = None
        min_usage = float('inf')
        
        for court in range(1, tournament.court_count + 1):
            if is_court_available(tournament, date, time, court):
                # Учитываем как текущую загрузку площадки, так и загрузку в это время
                current_usage = court_usage[court]
                if current_usage < min_usage:
                    min_usage = current_usage
                    best_court = court
        
        if best_court:
            return {
                'date': date,
                'time': time,
                'court': best_court
            }
    
    # Если не нашли подходящее время, возвращаем последний день на первую площадку
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
    """Проверка занятости участника с учетом времени матча и перерыва"""
    matches = Match.query.filter(
        (Match.participant1_id == participant_id) | (Match.participant2_id == participant_id),
        Match.tournament_id == tournament.id,
        Match.match_date == date
    ).all()
    
    check_datetime = datetime.combine(date, time)
    
    for match in matches:
        if match.match_time:
            match_start = datetime.combine(date, match.match_time)
            # Учитываем время матча + перерыв для более точной проверки конфликтов
            match_end = match_start + timedelta(minutes=tournament.match_duration + tournament.break_duration)
            
            # Проверяем, не пересекается ли время матча с проверяемым временем
            # Участник занят, если проверяемое время попадает в интервал матча + перерыва
            if match_start <= check_datetime < match_end:
                return True
    
    return False

def add_minutes_to_time(time, minutes):
    """Добавление минут к времени"""
    dt = datetime.combine(datetime.today(), time)
    new_dt = dt + timedelta(minutes=minutes)
    return new_dt.time()

def check_participant_conflicts(tournament, p1_id, p2_id, date, time):
    """Проверка конфликтов участников - не играют ли они одновременно на разных площадках"""
    # Проверяем, не играет ли участник 1 в это время
    p1_matches = Match.query.filter(
        (Match.participant1_id == p1_id) | (Match.participant2_id == p1_id),
        Match.tournament_id == tournament.id,
        Match.match_date == date
    ).all()
    
    # Проверяем, не играет ли участник 2 в это время
    p2_matches = Match.query.filter(
        (Match.participant1_id == p2_id) | (Match.participant2_id == p2_id),
        Match.tournament_id == tournament.id,
        Match.match_date == date
    ).all()
    
    check_datetime = datetime.combine(date, time)
    
    # Проверяем конфликты для участника 1
    for match in p1_matches:
        if match.match_time:
            match_start = datetime.combine(date, match.match_time)
            match_end = match_start + timedelta(minutes=tournament.match_duration + tournament.break_duration)
            
            if match_start <= check_datetime < match_end:
                return True, f"Участник {p1_id} уже играет в это время на площадке {match.court_number}"
    
    # Проверяем конфликты для участника 2
    for match in p2_matches:
        if match.match_time:
            match_start = datetime.combine(date, match.match_time)
            match_end = match_start + timedelta(minutes=tournament.match_duration + tournament.break_duration)
            
            if match_start <= check_datetime < match_end:
                return True, f"Участник {p2_id} уже играет в это время на площадке {match.court_number}"
    
    return False, None

def is_participant_recently_played(tournament, participant_id, date, time):
    """Проверка, не играл ли участник недавно (в предыдущем или следующем временном слоте)"""
    # Рассчитываем время предыдущего и следующего временных слотов
    slot_duration = tournament.match_duration + tournament.break_duration
    prev_time = add_minutes_to_time(time, -slot_duration)
    next_time = add_minutes_to_time(time, slot_duration)
    
    # Проверяем предыдущий временной слот
    if prev_time >= datetime.strptime('09:00', '%H:%M').time():
        prev_date = date
        if has_participant_match_at_time(tournament, participant_id, prev_date, prev_time):
            return True
    else:
        # Проверяем предыдущий день
        prev_date = date - timedelta(days=1)
        if prev_date >= tournament.start_date:
            # Находим последний временной слот предыдущего дня
            end_time = datetime.strptime('22:00', '%H:%M').time()
            end_dt = datetime.combine(prev_date, end_time)
            prev_dt = end_dt - timedelta(minutes=slot_duration)
            prev_time = prev_dt.time()
            if has_participant_match_at_time(tournament, participant_id, prev_date, prev_time):
                return True
    
    # Проверяем следующий временной слот
    if next_time <= datetime.strptime('22:00', '%H:%M').time():
        next_date = date
        if has_participant_match_at_time(tournament, participant_id, next_date, next_time):
            return True
    else:
        # Проверяем следующий день
        next_date = date + timedelta(days=1)
        if next_date <= tournament.end_date:
            # Находим первый временной слот следующего дня
            next_time = datetime.strptime('09:00', '%H:%M').time()
            if has_participant_match_at_time(tournament, participant_id, next_date, next_time):
                return True
    
    return False

def has_participant_match_at_time(tournament, participant_id, date, time):
    """Проверка, есть ли у участника матч в указанное время"""
    matches = Match.query.filter(
        (Match.participant1_id == participant_id) | (Match.participant2_id == participant_id),
        Match.tournament_id == tournament.id,
        Match.match_date == date
    ).all()
    
    for match in matches:
        if match.match_time:
            match_datetime = datetime.combine(date, match.match_time)
            check_datetime = datetime.combine(date, time)
            
            # Проверяем, что матч в том же временном слоте (с погрешностью 5 минут)
            if abs((match_datetime - check_datetime).total_seconds()) < 300:
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
        
        # Пересчитываем номера матчей в хронологическом порядке
        renumber_matches_chronologically(data['tournament_id'])
        
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
    participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
    
    # Проверяем и создаем недостающие матчи
    check_and_create_missing_matches(tournament_id)
    
    # Обновляем данные после возможного создания матчей
    matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
    
    # Создание шахматки и статистики
    chessboard = create_chessboard(participants, matches)
    statistics = calculate_statistics(participants, matches, tournament)
    
    # Записываем отладочную информацию в файл
    debug_chessboard_to_file(participants, matches, tournament_id)
    
    # Добавляем места участников на основе очков (сохраняем сортировку по имени)
    participants_with_stats = []
    for participant in participants:  # participants уже отсортированы по имени
        participant_stats = statistics.get(participant.id, {
            'games': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'points': 0, 'goal_difference': 0
        })
        participants_with_stats.append({
            'participant': participant,
            'stats': participant_stats
        })
    
    # Создаем отдельный список для расчета мест (сортированный по очкам)
    participants_for_ranking = participants_with_stats.copy()
    participants_for_ranking.sort(key=lambda x: (-x['stats']['points'], -x['stats']['goal_difference']))
    
    # Создаем словарь мест для быстрого поиска
    position_map = {}
    for i, item in enumerate(participants_for_ranking):
        position_map[item['participant'].id] = i + 1
    
    # Добавляем места к участникам в порядке добавления
    for item in participants_with_stats:
        item['position'] = position_map[item['participant'].id]
    
    # Определяем ближайшие матчи для каждой площадки отдельно
    now = datetime.now()
    upcoming_matches = [m for m in matches if m.status != 'завершен' and m.match_date and m.match_time and m.court_number]
    
    # Группируем матчи по площадкам
    matches_by_court = {}
    for match in upcoming_matches:
        court = match.court_number
        if court not in matches_by_court:
            matches_by_court[court] = []
        matches_by_court[court].append(match)
    
    # Для каждой площадки берем 2 ближайших матча
    next_match_ids = []
    for court in sorted(matches_by_court.keys()):
        court_matches = matches_by_court[court]
        court_matches.sort(key=lambda m: (m.match_date, m.match_time))
        # Берем первые 2 матча для каждой площадки
        for match in court_matches[:2]:
            next_match_ids.append(match.id)
    
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
    
    # Проверяем, есть ли недостающие матчи
    has_missing = has_missing_matches(tournament_id)
    
    return render_template('tournament.html', 
                         tournament=tournament, 
                         participants=participants, 
                         participants_data=participants_data,
                         participants_with_stats=participants_with_stats,
                         matches=matches,
                         matches_data=matches_data,
                         chessboard=chessboard,
                         statistics=statistics,
                         next_match_ids=next_match_ids,
                         has_missing_matches=has_missing)

def debug_chessboard_to_file(participants, matches, tournament_id):
    """Запись данных турнирной таблицы в файл для отладки"""
    try:
        with open(f'debug_chessboard_{tournament_id}.txt', 'w', encoding='utf-8') as f:
            f.write(f"=== ОТЛАДКА ТУРНИРНОЙ ТАБЛИЦЫ (Турнир ID: {tournament_id}) ===\n\n")
            
            # Информация об участниках
            f.write("УЧАСТНИКИ:\n")
            for i, p in enumerate(participants, 1):
                f.write(f"{i}. ID: {p.id}, Имя: '{p.name}', User ID: {p.user_id}\n")
            f.write(f"Всего участников: {len(participants)}\n\n")
            
            # Информация о матчах
            f.write("МАТЧИ:\n")
            for i, m in enumerate(matches, 1):
                f.write(f"{i}. ID: {m.id}, Участники: {m.participant1_id} vs {m.participant2_id}, "
                       f"Статус: {m.status}, Дата: {m.match_date}, Время: {m.match_time}, "
                       f"Площадка: {m.court_number}, Счет: {m.score1}:{m.score2}\n")
            f.write(f"Всего матчей: {len(matches)}\n\n")
            
            # Создаем шахматку для анализа
            chessboard = {}
            sorted_participants = sorted(participants, key=lambda p: p.name)
            
            f.write("СОЗДАНИЕ ШАХМАТКИ:\n")
            for p1 in sorted_participants:
                chessboard[p1.id] = {}
                f.write(f"\nСтрока для участника {p1.id} ('{p1.name}'):\n")
                
                for p2 in sorted_participants:
                    if p1.id == p2.id:
                        chessboard[p1.id][p2.id] = {'type': 'diagonal', 'value': '—'}
                        f.write(f"  [{p1.id}][{p2.id}] = диагональ (—)\n")
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
                                f.write(f"  [{p1.id}][{p2.id}] = результат ({score}) - матч {match.id}\n")
                            else:
                                chessboard[p1.id][p2.id] = {
                                    'type': 'upcoming',
                                    'value': f"{match.match_date.strftime('%d.%m')} {match.match_time.strftime('%H:%M')}",
                                    'match_id': match.id,
                                    'editable': False,
                                    'date': match.match_date,
                                    'time': match.match_time,
                                    'court': match.court_number
                                }
                                f.write(f"  [{p1.id}][{p2.id}] = запланирован ({match.match_date.strftime('%d.%m')} {match.match_time.strftime('%H:%M')}) - матч {match.id}\n")
                        else:
                            chessboard[p1.id][p2.id] = {'type': 'empty', 'value': ''}
                            f.write(f"  [{p1.id}][{p2.id}] = ПУСТОЙ (матч не найден!)\n")
            
            f.write(f"\n=== КОНЕЦ ОТЛАДКИ ===\n")
            
        logger.info(f"Данные турнирной таблицы записаны в файл debug_chessboard_{tournament_id}.txt")
        return True
    except Exception as e:
        logger.error(f"Ошибка при записи отладочного файла: {str(e)}")
        return False

def create_chessboard(participants, matches):
    """Создание шахматки для отображения результатов"""
    chessboard = {}
    
    # Сортируем участников по имени для консистентности
    sorted_participants = sorted(participants, key=lambda p: p.name)
    
    # Находим ближайшие игры для каждой площадки отдельно
    now = datetime.now()
    upcoming_matches = [m for m in matches if m.status != 'завершен' and m.match_date and m.match_time and m.court_number]
    
    # Группируем матчи по площадкам
    matches_by_court = {}
    for match in upcoming_matches:
        court = match.court_number
        if court not in matches_by_court:
            matches_by_court[court] = []
        matches_by_court[court].append(match)
    
    # Для каждой площадки берем 2 ближайших матча
    next_matches = []
    for court in sorted(matches_by_court.keys()):
        court_matches = matches_by_court[court]
        court_matches.sort(key=lambda m: (m.match_date, m.match_time))
        # Берем первые 2 матча для каждой площадки
        next_matches.extend(court_matches[:2])
    
    for p1 in sorted_participants:
        chessboard[p1.id] = {}
        for p2 in sorted_participants:
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
                        
                        # Определяем позицию в очереди ближайших игр для данной площадки
                        match_position = None
                        if match.court_number in matches_by_court:
                            court_matches = matches_by_court[match.court_number]
                            court_matches.sort(key=lambda m: (m.match_date, m.match_time))
                            for i in range(min(2, len(court_matches))):  # Берем только первые 2
                                court_match = court_matches[i]
                                if court_match.id == match.id:
                                    match_position = i + 1  # 1 - первая игра на площадке, 2 - вторая игра на площадке
                                    break
                        
                        chessboard[p1.id][p2.id] = {
                            'type': 'upcoming',
                            'value': f"{match.match_date.strftime('%d.%m')} {match.match_time.strftime('%H:%M')}",
                            'match_id': match.id,
                            'editable': False,
                            'date': match.match_date,
                            'time': match.match_time,
                            'court': match.court_number,
                            'is_next': match_position == 1,  # Флаг для выделения первой ближайшей игры
                            'is_second': match_position == 2  # Флаг для выделения второй ближайшей игры
                        }
                        
                        # Отладочная информация
                        if match_position in [1, 2]:
                            logger.info(f"Ближайший матч: {p1.name} vs {p2.name}, позиция: {match_position}, время: {match.match_date.strftime('%d.%m')} {match.match_time.strftime('%H:%M')}")
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
    app.run(debug=True, host='0.0.0.0', port=5000)
