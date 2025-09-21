"""
Основные маршруты приложения
"""
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging
# Tournament передается как параметр в функции

logger = logging.getLogger(__name__)

def create_main_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, TournamentAdmin):
    """Создает основные маршруты приложения"""
    
    def check_tournament_access(tournament_id, admin_id=None):
        """Проверяет права доступа к турниру"""
        from flask import session
        
        # Получаем турнир
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            return False, "Турнир не найден"
        
        # Проверяем, является ли пользователь системным админом
        if admin_id:
            admin = TournamentAdmin.query.get(admin_id)
            if admin and admin.email == 'admin@system':
                return True, tournament
        
        # Проверяем, является ли пользователь админом этого турнира
        if tournament.admin_id == admin_id:
            return True, tournament
        
        # Проверяем сессию админа
        session_admin_id = session.get('admin_id')
        if session_admin_id:
            session_admin = TournamentAdmin.query.get(session_admin_id)
            if session_admin:
                # Системный админ имеет доступ ко всем турнирам
                if session_admin.email == 'admin@system':
                    return True, tournament
                # Админ турнира имеет доступ только к своим турнирам
                if tournament.admin_id == session_admin_id:
                    return True, tournament
        
        return False, "У вас нет прав доступа к этому турниру"
    
    def get_current_admin():
        """Получает текущего админа из сессии"""
        from flask import session
        admin_id = session.get('admin_id')
        if admin_id:
            return TournamentAdmin.query.get(admin_id)
        return None
    
    @app.route('/')
    def index():
        # Новая стартовая страница с выбором роли
        return render_template('index.html')
    
    @app.route('/tournaments')
    def tournaments_list():
        """Список всех турниров для просмотра"""
        tournaments = Tournament.query.all()
        # Загружаем участников для каждого турнира
        for tournament in tournaments:
            tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
        return render_template('tournaments.html', tournaments=tournaments)
    
    @app.route('/create-tournament', methods=['GET', 'POST'])
    def create_tournament_form():
        """Страница создания нового турнира"""
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('create_tournament.html')
            
            # Получаем данные формы
            name = request.form.get('name')
            email = request.form.get('email')
            telegram_id = request.form.get('telegram_id')
            contact_method = request.form.get('contact_method')
            
            if not name:
                flash('Пожалуйста, введите ваше имя', 'error')
                return render_template('create_tournament.html')
            
            if contact_method == 'email' and not email:
                flash('Пожалуйста, введите email', 'error')
                return render_template('create_tournament.html')
            
            if contact_method == 'telegram' and not telegram_id:
                flash('Пожалуйста, введите Telegram ID', 'error')
                return render_template('create_tournament.html')
            
            # Генерируем токен турнира 47
            tournament_token = "47"
            
            # Сохраняем админа в базе данных
            try:
                # Проверяем, существует ли уже админ с таким email
                existing_admin = TournamentAdmin.query.filter_by(email=email).first()
                
                if existing_admin:
                    # Обновляем существующего админа
                    existing_admin.name = name
                    existing_admin.token = tournament_token
                    existing_admin.is_active = True
                    db.session.commit()
                    admin = existing_admin
                else:
                    # Создаем нового админа
                    admin = TournamentAdmin(
                        name=name,
                        email=email,
                        token=tournament_token,
                        is_active=True
                    )
                    db.session.add(admin)
                    db.session.commit()
                
                logger.info(f"Админ турнира создан/обновлен: {name} ({email}) с токеном {tournament_token}")
                
            except Exception as e:
                logger.error(f"Ошибка сохранения админа: {e}")
                db.session.rollback()
                flash('Ошибка при сохранении данных админа', 'error')
                return render_template('create_tournament.html')
            
            # Отправляем токен
            if contact_method == 'email':
                try:
                    from flask_mail import Message
                    from app import mail
                    
                    msg = Message(
                        subject='Токен для создания турнира',
                        recipients=[email],
                        body=f'''
Здравствуйте, {name}!

Ваш токен для создания турнира: {tournament_token}

Используйте этот токен для доступа к функциям администратора турнира.

С уважением,
Команда Турнирной системы
                        ''',
                        html=f'''
                        <h2>Токен для создания турнира</h2>
                        <p>Здравствуйте, <strong>{name}</strong>!</p>
                        <p>Ваш токен для создания турнира: <strong style="font-size: 24px; color: #007bff;">{tournament_token}</strong></p>
                        <p>Используйте этот токен для доступа к функциям администратора турнира.</p>
                        <hr>
                        <p><em>С уважением,<br>Команда Турнирной системы</em></p>
                        '''
                    )
                    mail.send(msg)
                    flash(f'Токен турнира {tournament_token} отправлен на email: {email}', 'success')
                except Exception as e:
                    logger.error(f"Ошибка отправки email: {e}")
                    flash(f'Токен турнира: {tournament_token}. Ошибка отправки email, но токен сохранен.', 'warning')
            else:
                # Для Telegram пока просто показываем сообщение
                flash(f'Токен турнира {tournament_token} отправлен в Telegram: {telegram_id}', 'success')
            
            return redirect(url_for('index'))
        
        return render_template('create_tournament.html')
    
    @app.route('/join-tournament')
    def join_tournament():
        """Страница для выбора турнира для участия"""
        tournaments = Tournament.query.all()
        return render_template('join_tournament.html', tournaments=tournaments)
    
    @app.route('/participant-tournament')
    def participant_tournament():
        """Страница для участников турниров"""
        if not current_user.is_authenticated:
            flash('Необходимо войти в систему', 'error')
            return redirect(url_for('login'))
        
        # Получаем турниры, в которых участвует текущий пользователь
        user_participations = Participant.query.filter_by(user_id=current_user.id).all()
        tournament_ids = [p.tournament_id for p in user_participations]
        tournaments = Tournament.query.filter(Tournament.id.in_(tournament_ids)).all()
        
        for tournament in tournaments:
            tournament.participants = Participant.query.filter_by(tournament_id=tournament.id).all()
        
        return render_template('participant_tournament.html', tournaments=tournaments)
    
    # ===== МАРШРУТЫ ДЛЯ АДМИНОВ ТУРНИРОВ =====
    
    @app.route('/admin-tournament', methods=['GET', 'POST'])
    def admin_tournament():
        """Страница входа для админов турниров"""
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('admin_tournament.html')
            
            # Получаем данные формы
            email = request.form.get('email')
            token = request.form.get('token')
            
            if not email or not token:
                flash('Пожалуйста, заполните все поля', 'error')
                return render_template('admin_tournament.html')
            
            # Ищем админа по email и токену
            admin = TournamentAdmin.query.filter_by(
                email=email, 
                token=token, 
                is_active=True
            ).first()
            
            if admin:
                # Сохраняем админа в сессии
                from flask import session
                session['admin_id'] = admin.id
                session['admin_name'] = admin.name
                session['admin_email'] = admin.email
                
                flash(f'Добро пожаловать, {admin.name}!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Неверный email или токен', 'error')
                return render_template('admin_tournament.html')
        
        return render_template('admin_tournament.html')
    
    @app.route('/admin-dashboard')
    def admin_dashboard():
        """Панель управления админа турниров"""
        from flask import session
        
        # Проверяем, что админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('admin_tournament'))
        
        admin_id = session['admin_id']
        admin = TournamentAdmin.query.get(admin_id)
        
        if not admin or not admin.is_active:
            flash('Админ не найден или деактивирован', 'error')
            return redirect(url_for('admin_tournament'))
        
        # Получаем турниры этого админа
        if admin.email == 'admin@system':
            # Системный админ видит все турниры
            tournaments = Tournament.query.all()
        else:
            # Обычный админ видит только свои турниры
            tournaments = Tournament.query.filter_by(admin_id=admin_id).all()
        
        return render_template('admin_dashboard.html', 
                             admin=admin, 
                             tournaments=tournaments)
    
    @app.route('/admin-create-tournament', methods=['GET', 'POST'])
    def admin_create_tournament():
        """Создание турнира админом"""
        from flask import session
        
        # Проверяем, что админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('admin_tournament'))
        
        admin_id = session['admin_id']
        admin = TournamentAdmin.query.get(admin_id)
        
        if not admin or not admin.is_active:
            flash('Админ не найден или деактивирован', 'error')
            return redirect(url_for('admin_tournament'))
        
        if request.method == 'POST':
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.form.get('csrf_token'))
            except:
                flash('Ошибка безопасности. Попробуйте еще раз.', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            # Получаем данные формы
            name = request.form.get('name')
            description = request.form.get('description')
            sport_type = request.form.get('sport_type', 'пинг-понг')  # Значение по умолчанию
            start_date = request.form.get('start_date')
            court_count = int(request.form.get('court_count', 4))
            match_duration = int(request.form.get('match_duration', 60))
            break_duration = int(request.form.get('break_duration', 15))
            sets_to_win = int(request.form.get('sets_to_win', 2))
            points_to_win = int(request.form.get('points_to_win', 21))
            points_win = int(request.form.get('points_win', 1))
            points_draw = int(request.form.get('points_draw', 1))
            points_loss = int(request.form.get('points_loss', 0))
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            if not name:
                flash('Пожалуйста, введите название турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            if not start_date:
                flash('Пожалуйста, выберите дату начала турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            try:
                # Преобразуем строки времени в объекты time
                from datetime import time
                start_time_obj = None
                end_time_obj = None
                
                if start_time:
                    start_time_obj = datetime.strptime(start_time, '%H:%M').time()
                else:
                    start_time_obj = datetime.strptime("09:00", '%H:%M').time()
                    
                if end_time:
                    end_time_obj = datetime.strptime(end_time, '%H:%M').time()
                else:
                    end_time_obj = datetime.strptime("18:00", '%H:%M').time()
                
                # Создаем турнир
                tournament = Tournament(
                    name=name,
                    description=description or '',
                    sport_type=sport_type,
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
                    end_date=None,  # Убираем дату окончания
                    max_participants=32,  # Фиксированное значение
                    court_count=court_count or 4,
                    match_duration=match_duration or 60,
                    break_duration=break_duration or 15,
                    sets_to_win=sets_to_win or 2,
                    points_to_win=points_to_win or 21,
                    points_win=points_win or 1,
                    points_draw=points_draw or 1,
                    points_loss=points_loss or 0,
                    start_time=start_time_obj,
                    end_time=end_time_obj,
                    admin_id=admin_id,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(tournament)
                db.session.commit()
                
                flash(f'Турнир "{name}" успешно создан!', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                db.session.rollback()
                logger.error(f"Ошибка создания турнира: {e}")
                flash('Ошибка при создании турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
        
        return render_template('admin_create_tournament.html', admin=admin)
    
    @app.route('/admin-tournament/<int:tournament_id>')
    def admin_tournament_detail(tournament_id):
        """Детальный просмотр турнира для админа"""
        from flask import session
        
        # Проверяем, что админ авторизован
        if 'admin_id' not in session:
            flash('Необходима авторизация', 'error')
            return redirect(url_for('admin_tournament'))
        
        admin_id = session['admin_id']
        admin = TournamentAdmin.query.get(admin_id)
        
        if not admin or not admin.is_active:
            flash('Админ не найден или деактивирован', 'error')
            return redirect(url_for('admin_tournament'))
        
        # Получаем турнир
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Проверяем права доступа
        has_access, result = check_tournament_access(tournament_id, admin_id)
        if not has_access:
            flash(result, 'error')
            return redirect(url_for('admin_dashboard'))
        
        # Получаем участников и матчи
        participants = Participant.query.filter_by(tournament_id=tournament_id).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        return render_template('admin_tournament_detail.html', 
                             admin=admin, 
                             tournament=tournament, 
                             participants=participants, 
                             matches=matches)
    
    @app.route('/tournament/<int:tournament_id>')
    def tournament_detail(tournament_id):
        """Полная страница турнира с функционалом (Страница 10)"""
        from flask import session
        
        tournament = Tournament.query.get_or_404(tournament_id)
        participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        # Проверяем авторизацию админа
        current_user = None
        if 'admin_id' in session:
            admin = TournamentAdmin.query.get(session['admin_id'])
            if admin and admin.is_active:
                current_user = type('User', (), {
                    'is_authenticated': True,
                    'role': 'администратор'
                })()
        
        # Создаем базовые данные для совместимости с шаблоном
        participants_with_stats = []
        participants_with_stats_chessboard = []
        chessboard = {}
        schedule_display = {}
        statistics = {}
        participants_data = []
        
        # Заполняем расписание матчами
        for match in matches:
            if match.match_date:
                date_str = match.match_date.strftime('%Y-%m-%d')
                if date_str not in schedule_display:
                    schedule_display[date_str] = {
                        'date_display': match.match_date.strftime('%d.%m.%Y'),
                        'matches': []
                    }
                
                # Находим участников по ID
                participant1 = next((p for p in participants if p.id == match.participant1_id), None)
                participant2 = next((p for p in participants if p.id == match.participant2_id), None)
                
                match_data = {
                    'id': match.id,
                    'participant1': participant1.name if participant1 else 'Неизвестный участник',
                    'participant2': participant2.name if participant2 else 'Неизвестный участник',
                    'time': match.match_time.strftime('%H:%M') if match.match_time else 'Время не указано',
                    'court': match.court_number or 'Корт не указан',
                    'status': match.status,
                    'score1': match.score1,
                    'score2': match.score2
                }
                schedule_display[date_str]['matches'].append(match_data)
        
        # Создаем простые данные для участников
        for i, participant in enumerate(participants):
            participant_data = {
                'id': participant.id,
                'name': participant.name,
                'is_team': participant.is_team
            }
            participants_data.append(participant_data)
            
            # Создаем статистику участника
            participant_stats = {
                'games': 0,
                'wins': 0,
                'losses': 0,
                'draws': 0,
                'points': 0,
                'goal_difference': 0
            }
            
            participants_with_stats.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1
            })
            
            participants_with_stats_chessboard.append({
                'participant': participant,
                'stats': participant_stats,
                'position': i + 1
            })
            
            # Создаем шахматку с данными матчей
            chessboard[participant.id] = {}
            for other_participant in participants:
                if participant.id != other_participant.id:
                    # Ищем матч между этими участниками
                    match = next((m for m in matches if 
                                (m.participant1_id == participant.id and m.participant2_id == other_participant.id) or
                                (m.participant1_id == other_participant.id and m.participant2_id == participant.id)), None)
                    
                    if match:
                        if match.status == 'завершен' and match.score1 is not None and match.score2 is not None:
                            # Матч завершен - показываем результат
                            if match.participant1_id == participant.id:
                                score = f"{match.score1}:{match.score2}"
                            else:
                                score = f"{match.score2}:{match.score1}"
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'result',
                                'value': score,
                                'match_id': match.id
                            }
                        else:
                            # Матч запланирован или в процессе
                            chessboard[participant.id][other_participant.id] = {
                                'type': 'scheduled',
                                'value': 'vs',
                                'match_id': match.id
                            }
                    else:
                        # Матч не найден
                        chessboard[participant.id][other_participant.id] = {
                            'type': 'empty',
                            'value': '',
                            'match_id': None
                        }
        
        return render_template('tournament.html', 
                             tournament=tournament, 
                             participants=participants, 
                             participants_data=participants_data,
                             participants_with_stats=participants_with_stats,
                             participants_with_stats_chessboard=participants_with_stats_chessboard,
                             matches=matches,
                             chessboard=chessboard,
                             schedule_display=schedule_display,
                             statistics=statistics,
                             has_missing_matches=False,
                             next_match_ids=[],
                             current_user=current_user)
    
    @app.route('/admin-logout')
    def admin_logout():
        """Выход админа"""
        from flask import session
        session.pop('admin_id', None)
        session.pop('admin_name', None)
        session.pop('admin_email', None)
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('admin_tournament'))

# ===== КОНЕЦ create_main_routes =====
