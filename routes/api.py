"""
API маршруты приложения
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date, time
import logging

logger = logging.getLogger(__name__)

def create_smart_schedule(tournament, participants, Match, db):
    """
    Создает расписание матчей по раундам согласно новому алгоритму:
    1. Определение количества матчей и раундов
    2. Распределение матчей по раундам и площадкам
    3. Расчет времени каждого раунда
    4. Итоговая схема времени
    """
    from datetime import date, time, timedelta
    import random
    
    # Параметры турнира
    n = len(participants)  # число участников
    k = tournament.court_count or 4  # число площадок
    time_match = tournament.match_duration or 15  # длительность матча в минутах
    time_break = tournament.break_duration or 2  # длительность перерыва в минутах
    start_time = tournament.start_time or time(9, 0)
    end_time = tournament.end_time or time(18, 0)
    start_date = tournament.start_date or date.today()
    
    if n < 2:
        return 0
    
    # Шаг 1: Определение количества матчей и раундов
    # Общее число матчей: M = n(n-1)/2
    total_matches = n * (n - 1) // 2
    
    # Число раундов: R = n-1 (для четного числа участников)
    # Если нечетное, добавляем фиктивного участника
    is_odd = n % 2 == 1
    if is_odd:
        R = n  # для нечетного числа участников
    else:
        R = n - 1
    
    # Шаг 2: Создание списка всех матчей (каждый с каждым)
    matches_to_schedule = []
    for i in range(n):
        for j in range(i + 1, n):
            matches_to_schedule.append((participants[i], participants[j]))
    
    # Перемешиваем матчи для случайности
    random.shuffle(matches_to_schedule)
    
    # Шаг 3: Умное распределение матчей с проверкой конфликтов
    scheduled_matches = []
    match_number = 1
    current_date = start_date
    current_time = start_time
    
    # Словарь для отслеживания занятости участников по времени
    participant_schedule = {}  # {participant_id: {time: court_number}}
    court_schedule = {}  # {court_number: {time: participant_ids}}
    
    for match in matches_to_schedule:
        participant1, participant2 = match
        p1_id, p2_id = participant1.id, participant2.id
        
        # Ищем свободное время для обоих участников
        match_scheduled = False
        temp_time = current_time
        temp_date = current_date
        
        while not match_scheduled:
            # Проверяем, свободны ли оба участника в это время
            # Участник свободен, если он не играет в это время И не играет в течение времени матча
            p1_free = True
            p2_free = True
            
            if p1_id in participant_schedule:
                for scheduled_time in participant_schedule[p1_id]:
                    # Проверяем пересечение времени: если матч начинается в temp_time и длится time_match минут
                    # то он заканчивается в temp_time + time_match
                    # Если есть пересечение с уже запланированным матчем, то участник занят
                    scheduled_end_time = add_minutes_to_time(scheduled_time, time_match)
                    temp_end_time = add_minutes_to_time(temp_time, time_match)
                    
                    # Проверяем пересечение интервалов времени
                    if (temp_time < scheduled_end_time and temp_end_time > scheduled_time):
                        p1_free = False
                        break
            
            if p2_id in participant_schedule:
                for scheduled_time in participant_schedule[p2_id]:
                    scheduled_end_time = add_minutes_to_time(scheduled_time, time_match)
                    temp_end_time = add_minutes_to_time(temp_time, time_match)
                    
                    if (temp_time < scheduled_end_time and temp_end_time > scheduled_time):
                        p2_free = False
                        break
            
            if p1_free and p2_free:
                # Ищем свободную площадку
                for court_num in range(1, k + 1):
                    court_free = True
                    
                    if court_num in court_schedule:
                        for scheduled_time in court_schedule[court_num]:
                            scheduled_end_time = add_minutes_to_time(scheduled_time, time_match)
                            temp_end_time = add_minutes_to_time(temp_time, time_match)
                            
                            if (temp_time < scheduled_end_time and temp_end_time > scheduled_time):
                                court_free = False
                                break
                    
                    if court_free:
                        # Найдено свободное время и площадка
                        match_start_time = temp_time
            
            # Создаем матч
                        match_obj = Match(
                tournament_id=tournament.id,
                            participant1_id=p1_id,
                            participant2_id=p2_id,
                status='запланирован',
                            match_date=temp_date,
                match_time=match_start_time,
                            court_number=court_num,
                match_number=match_number
            )
                        db.session.add(match_obj)
                        scheduled_matches.append(match_obj)
            match_number += 1
                        
                        # Обновляем расписания
                        if p1_id not in participant_schedule:
                            participant_schedule[p1_id] = {}
                        if p2_id not in participant_schedule:
                            participant_schedule[p2_id] = {}
                        if court_num not in court_schedule:
                            court_schedule[court_num] = {}
                        
                        participant_schedule[p1_id][temp_time] = court_num
                        participant_schedule[p2_id][temp_time] = court_num
                        court_schedule[court_num][temp_time] = {p1_id, p2_id}
                        
                        match_scheduled = True
                        break
                
                if not match_scheduled:
                    # Нет свободных площадок в это время, переходим к следующему времени
                    temp_time = add_minutes_to_time(temp_time, time_match + time_break)
                    
                    # Проверяем, не выходим ли за пределы рабочего дня
                    if temp_time > end_time:
                        temp_date += timedelta(days=1)
                        temp_time = start_time
            else:
                # Один из участников занят, переходим к следующему времени
                temp_time = add_minutes_to_time(temp_time, time_match + time_break)
                
                # Проверяем, не выходим ли за пределы рабочего дня
                if temp_time > end_time:
                    temp_date += timedelta(days=1)
                    temp_time = start_time
    
    return len(scheduled_matches)


def add_minutes_to_time(time_obj, minutes):
    """Добавляет минуты к времени"""
    from datetime import datetime, timedelta
    dt = datetime.combine(date.today(), time_obj)
    new_dt = dt + timedelta(minutes=minutes)
    return new_dt.time()

def create_api_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, Token):
    """Создает API маршруты приложения"""
    
    # ===== ПОЛЬЗОВАТЕЛИ =====
    
    @app.route('/api/users', methods=['POST'])
    def create_user():
        """Создание нового пользователя (регистрация)"""
        data = request.get_json()
        
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Необходимы имя пользователя и пароль'}), 400
        
        # Проверяем, существует ли пользователь
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Участник с таким именем уже существует'}), 400
        
        try:
            # Создаем нового пользователя
            user = User(
                username=data['username'],
                password_hash=generate_password_hash(data['password']),
                role=data.get('role', 'участник')
            )
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Создан новый участник: {data['username']} (ID: {user.id})")
            return jsonify({
                'success': True,
                'message': 'Участник успешно создан',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'role': user.role
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при создании пользователя: {str(e)}")
            return jsonify({'error': 'Ошибка при создании пользователя'}), 500

    @app.route('/api/users/<int:user_id>/role', methods=['PUT'])
    @login_required
    def change_user_role(user_id):
        """Изменение роли пользователя"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        data = request.get_json()
        if not data or 'role' not in data:
            return jsonify({'error': 'Необходима роль'}), 400
        
        user = User.query.get_or_404(user_id)
        old_role = user.role
        user.role = data['role']
        db.session.commit()
        
        logger.info(f"Роль пользователя {user.username} изменена с {old_role} на {user.role}")
        return jsonify({'success': True, 'message': 'Роль успешно изменена'})

    @app.route('/api/users', methods=['GET'])
    @login_required
    def get_users():
        """Получение списка пользователей"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        # Получаем ID турнира из параметров запроса
        tournament_id = request.args.get('tournament_id')
        
        if tournament_id:
            # Получаем участников турнира
            tournament_participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            participant_user_ids = [p.user_id for p in tournament_participants if p.user_id]
            
            # Исключаем пользователей, которые уже участвуют в турнире
            users = User.query.filter(~User.id.in_(participant_user_ids)).all()
        else:
            users = User.query.all()
        
        return jsonify([{
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': user.created_at.isoformat()
        } for user in users])

    @app.route('/api/users/<int:user_id>', methods=['DELETE'])
    @login_required
    def delete_user(user_id):
        """Удаление пользователя"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        user = User.query.get_or_404(user_id)
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"Участник {username} удален")
        return jsonify({'success': True, 'message': 'Участник успешно удален'})

    # ===== ТУРНИРЫ =====
    
    @app.route('/api/tournaments', methods=['POST'])
    @login_required
    def create_tournament():
        """Создание нового турнира"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        data = request.get_json()
        if not data or not data.get('name'):
            return jsonify({'error': 'Необходимо название турнира'}), 400
        
        try:
            tournament = Tournament(
                name=data['name'],
                sport_type=data.get('sport_type', 'теннис'),
                start_date=datetime.strptime(data.get('start_date', '2024-01-01'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(data.get('end_date', '2024-01-07'), '%Y-%m-%d').date(),
                max_participants=data.get('max_participants', 32),
                court_count=data.get('court_count', 3),
                match_duration=data.get('match_duration', 60),
                break_duration=data.get('break_duration', 15),
                start_time=datetime.strptime(data.get('start_time', '09:00'), '%H:%M').time(),
                end_time=datetime.strptime(data.get('end_time', '17:00'), '%H:%M').time(),
                points_win=data.get('points_win', 3),
                points_draw=data.get('points_draw', 1),
                points_loss=data.get('points_loss', 0),
                points_to_win=data.get('points_to_win', 21),
                sets_to_win=data.get('sets_to_win', 2)
            )
            db.session.add(tournament)
            db.session.commit()
            
            logger.info(f"Создан новый турнир: {tournament.name} (ID: {tournament.id})")
            return jsonify({
                'message': 'Турнир успешно создан',
                'tournament': {
                    'id': tournament.id,
                    'name': tournament.name,
                    'sport_type': tournament.sport_type
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при создании турнира: {str(e)}")
            return jsonify({'error': 'Ошибка при создании турнира'}), 500

    # ===== МАТЧИ =====
    
    @app.route('/api/matches/<int:match_id>', methods=['GET'])
    def get_match(match_id):
        """Получение информации о матче"""
        from flask import session
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'error': 'Необходима авторизация'}), 401
        
        # Простая заглушка для админа
        admin = type('Admin', (), {'id': session['admin_id'], 'is_active': True})()
        if not admin or not admin.is_active:
            return jsonify({'error': 'Неверная авторизация'}), 401
        
        match = Match.query.get_or_404(match_id)
        
        # Проверяем права (создатель турнира или системный админ)
        tournament = Tournament.query.get(match.tournament_id)
        if not tournament:
            return jsonify({'error': 'Турнир не найден'}), 404
            
        if admin.id != tournament.admin_id and admin.email != 'admin@system':
            return jsonify({'error': 'Недостаточно прав для просмотра матча'}), 403
        
        return jsonify({
            'success': True,
            'match': {
                'id': match.id,
                'tournament_id': match.tournament_id,
                'participant1_id': match.participant1_id,
                'participant2_id': match.participant2_id,
                'score1': match.score1,
                'score2': match.score2,
                'score': match.score,
                'sets_won_1': match.sets_won_1,
                'sets_won_2': match.sets_won_2,
                'winner_id': match.winner_id,
                'match_date': match.match_date.isoformat() if match.match_date else None,
                'match_time': match.match_time.isoformat() if match.match_time else None,
                'court_number': match.court_number,
                'match_number': match.match_number,
                'status': match.status,
                'created_at': match.created_at.isoformat(),
                'updated_at': match.updated_at.isoformat(),
                # Данные сетов
                'set1_score1': match.set1_score1,
                'set1_score2': match.set1_score2,
                'set2_score1': match.set2_score1,
                'set2_score2': match.set2_score2,
                'set3_score1': match.set3_score1,
                'set3_score2': match.set3_score2
            }
        })

    # ===== ТУРНИРЫ (дополнительные маршруты) =====
    
    @app.route('/api/tournaments/<int:tournament_id>/participants', methods=['POST'])
    def add_participant(tournament_id):
        """Добавление участника в турнир"""
        tournament = Tournament.query.get_or_404(tournament_id)
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'success': False, 'error': 'Необходимо имя участника'}), 400
        
        # Проверяем дубликаты
        existing_participant = Participant.query.filter_by(
            tournament_id=tournament_id,
            name=data['name']
        ).first()
        
        if existing_participant:
            return jsonify({'success': False, 'error': f'Участник с именем "{data["name"]}" уже существует в турнире'}), 400
        
        # Если указан user_id, проверяем, что пользователь не участвует в турнире
        if data.get('user_id'):
            existing_user_participant = Participant.query.filter_by(
                tournament_id=tournament_id,
                user_id=data['user_id']
            ).first()
            
            if existing_user_participant:
                return jsonify({'success': False, 'error': f'Участник уже участвует в турнире'}), 400
        
        try:
            participant = Participant(
                tournament_id=tournament_id,
                name=data['name'],
                is_team=data.get('is_team', False),
                user_id=data.get('user_id')
            )
            db.session.add(participant)
            db.session.commit()
            
            # Автоматически создаем расписание после добавления участника
            participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            if len(participants) >= 2:  # Минимум 2 участника для создания расписания
                # Удаляем существующие матчи
                Match.query.filter_by(tournament_id=tournament_id).delete()
                db.session.commit()
                
                # Создаем новое расписание
                matches_created = create_smart_schedule(tournament, participants, Match, db)
                db.session.commit()
                
                logger.info(f"Автоматически создано {matches_created} матчей для турнира {tournament_id}")
            
            return jsonify({
                'success': True,
                'participant': {
                    'id': participant.id,
                    'name': participant.name,
                    'is_team': participant.is_team
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении участника: {str(e)}")
            return jsonify({'success': False, 'error': 'Ошибка при добавлении участника'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/participants/<int:participant_id>', methods=['DELETE'])
    def delete_participant(tournament_id, participant_id):
        """Удаление участника из турнира"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Ошибка безопасности. Неверный CSRF токен.'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        tournament = Tournament.query.get_or_404(tournament_id)
        participant = Participant.query.filter_by(id=participant_id, tournament_id=tournament_id).first()
        
        if not participant:
            return jsonify({'success': False, 'error': 'Участник не найден'}), 404
        
        # Простая заглушка для админа
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        admin = type('Admin', (), {'id': admin_id, 'email': admin_email, 'is_active': True})()
        
        if not admin or not admin.is_active:
            return jsonify({'success': False, 'error': 'Неверная авторизация'}), 401
        
        # Проверяем права (создатель турнира или системный админ)
        if admin.id != tournament.admin_id and admin.email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав для удаления участника'}), 403
        
        try:
            participant_name = participant.name
            
            # Удаляем только матчи с участием удаляемого участника
            matches_to_delete = Match.query.filter(
                (Match.participant1_id == participant_id) | 
                (Match.participant2_id == participant_id)
            ).all()
            
            for match in matches_to_delete:
                db.session.delete(match)
            
            # Удаляем участника
            db.session.delete(participant)
            db.session.commit()
            
            logger.info(f"Участник '{participant_name}' удален из турнира {tournament_id}. Удалено {len(matches_to_delete)} матчей с его участием. Результаты других матчей сохранены.")
            logger.info(f"Участник '{participant_name}' (ID: {participant_id}) удален из турнира {tournament_id} админом {admin.email}")
            return jsonify({'success': True, 'message': f'Участник "{participant_name}" успешно удален. Результаты матчей других участников сохранены.'}), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении участника {participant_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении участника'}), 500

    @app.route('/api/tournaments/<int:tournament_id>', methods=['DELETE'])
    def delete_tournament(tournament_id):
        """Удаление турнира"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'error': 'Необходима авторизация'}), 401
        
        # Простая заглушка для админа
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        admin = type('Admin', (), {'id': admin_id, 'email': admin_email, 'is_active': True})()
        if not admin or not admin.is_active:
            return jsonify({'error': 'Неверная авторизация'}), 401
        
        # Проверяем права (создатель турнира или системный админ)
        if admin.id != tournament.admin_id and admin.email != 'admin@system':
            return jsonify({'error': 'Недостаточно прав для удаления турнира'}), 403
        
        try:
            # Удаляем все связанные данные
            # 1. Удаляем матчи
            Match.query.filter_by(tournament_id=tournament_id).delete()
            
            # 2. Удаляем участников
            Participant.query.filter_by(tournament_id=tournament_id).delete()
            
            # 3. Удаляем турнир
            tournament_name = tournament.name
            db.session.delete(tournament)
            
            db.session.commit()
            
            logger.info(f"Турнир '{tournament_name}' (ID: {tournament_id}) удален админом {admin.email}")
            return jsonify({
                'success': True, 
                'message': f'Турнир "{tournament_name}" успешно удален'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении турнира {tournament_id}: {str(e)}")
            return jsonify({'error': 'Ошибка при удалении турнира'}), 500

    # ===== МАТЧИ (дополнительные маршруты) =====
    
    @app.route('/api/matches', methods=['POST'])
    def create_match():
        """Создание нового матча с результатами"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        # Простая заглушка для админа
        admin = type('Admin', (), {'id': session['admin_id'], 'is_active': True})()
        if not admin or not admin.is_active:
            return jsonify({'success': False, 'error': 'Неверная авторизация'}), 401
        
        data = request.get_json()
        logger.info(f"Получены данные для создания матча: {data}")
        
        if not data or not data.get('tournament_id'):
            logger.error("Отсутствует tournament_id в данных")
            return jsonify({'success': False, 'error': 'Необходим ID турнира'}), 400
        
        try:
            # Создаем базовый матч
            match = Match(
                tournament_id=data['tournament_id'],
                participant1_id=data.get('participant1_id'),
                participant2_id=data.get('participant2_id'),
                match_date=datetime.strptime(data.get('match_date', '2024-01-01'), '%Y-%m-%d').date() if data.get('match_date') else None,
                match_time=datetime.strptime(data.get('match_time', '12:00'), '%H:%M').time() if data.get('match_time') else None,
                court_number=data.get('court_number'),
                match_number=data.get('match_number'),
                status=data.get('status', 'запланирован')
            )
            
            # Если есть данные сетов, заполняем их
            if data.get('sets'):
                sets_data = data['sets']
                logger.info(f"Обрабатываем данные сетов: {sets_data}")
                
                # Заполняем сеты
                for set_data in sets_data:
                    set_number = set_data.get('set_number')
                    score1 = set_data.get('score1', 0)
                    score2 = set_data.get('score2', 0)
                    
                    logger.info(f"Сет {set_number}: {score1}:{score2}")
                    
                    if set_number == 1:
                        match.set1_score1 = score1
                        match.set1_score2 = score2
                    elif set_number == 2:
                        match.set2_score1 = score1
                        match.set2_score2 = score2
                    elif set_number == 3:
                        match.set3_score1 = score1
                        match.set3_score2 = score2
                
                # Устанавливаем общий результат
                if data.get('sets_won_1') is not None and data.get('sets_won_2') is not None:
                    match.sets_won_1 = data['sets_won_1']
                    match.sets_won_2 = data['sets_won_2']
                    
                    # Определяем статус матча
                    if match.sets_won_1 > match.sets_won_2 or match.sets_won_2 > match.sets_won_1:
                        match.status = 'завершен'
                    else:
                        match.status = 'играют'
            
            db.session.add(match)
            db.session.commit()
            
            logger.info(f"Создан матч {match.id} в турнире {data['tournament_id']} с результатами")
            return jsonify({
                'success': True,
                'message': 'Матч успешно создан',
                'match': {
                    'id': match.id,
                    'tournament_id': match.tournament_id,
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id,
                    'status': match.status
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при создании матча: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при создании матча: {str(e)}'}), 500

    @app.route('/api/matches/<int:match_id>', methods=['PUT'])
    def update_match(match_id):
        """Обновление матча"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'error': 'Необходима авторизация'}), 401
        
        # Простая заглушка для админа
        admin = type('Admin', (), {'id': session['admin_id'], 'is_active': True})()
        if not admin or not admin.is_active:
            return jsonify({'error': 'Неверная авторизация'}), 401
        
        match = Match.query.get_or_404(match_id)
        
        # Проверяем права (создатель турнира или системный админ)
        tournament = Tournament.query.get(match.tournament_id)
        if not tournament:
            return jsonify({'error': 'Турнир не найден'}), 404
            
        if admin.id != tournament.admin_id and admin.email != 'admin@system':
            return jsonify({'error': 'Недостаточно прав для изменения матча'}), 403
        
        data = request.get_json()
        
        try:
            # Обработка новой структуры с сетами
            if 'sets' in data and data['sets']:
                sets_data = data['sets']
                
                # Сохраняем результат матча в формате "2:1"
                if 'result' in data:
                    match.score = data['result']
                
                # Определяем победителя на основе выигранных сетов
                if 'sets_won_1' in data and 'sets_won_2' in data:
                    sets_won_1 = data['sets_won_1']
                    sets_won_2 = data['sets_won_2']
                    
                    # Сохраняем количество выигранных сетов
                    match.sets_won_1 = sets_won_1
                    match.sets_won_2 = sets_won_2
                    
                    if sets_won_1 > sets_won_2:
                        match.winner_id = match.participant1_id
                    elif sets_won_2 > sets_won_1:
                        match.winner_id = match.participant2_id
                    else:
                        match.winner_id = None  # Ничья
                
                # Получаем настройки турнира для проверки правил
                tournament = Tournament.query.get(match.tournament_id)
                points_to_win = tournament.points_to_win if tournament else 21
                
                # Проверяем правильность результатов сетов
                for set_data in sets_data:
                    set_number = set_data.get('set_number', 1)
                    score1 = set_data.get('score1', 0)
                    score2 = set_data.get('score2', 0)
                    completed = set_data.get('completed', False)
                    
                    # Проверяем валидность счета
                    if score1 > 0 and score2 > 0:
                        difference = abs(score1 - score2)
                        
                        # Если кто-то набрал больше очков для победы, проверяем разницу
                        if score1 > points_to_win or score2 > points_to_win:
                            if difference > 2:
                                return jsonify({
                                    'success': False,
                                    'error': f'Неверный счет в сете {set_number}: {score1}:{score2}. Если разница {difference} > 2, то сет должен быть завершен. Максимальный счет: {min(score1, score2) + 2}:{min(score1, score2)}'
                                }), 400
                        
                        # Если сет помечен как завершенный, проверяем правила победы
                        if completed:
                            # Проверяем: кто-то набрал необходимое количество очков И разница больше 1
                            if not ((score1 >= points_to_win or score2 >= points_to_win) and difference > 1):
                                return jsonify({
                                    'success': False,
                                    'error': f'Сет {set_number} не может быть завершен со счетом {score1}:{score2}. Для победы нужно набрать {points_to_win} очков с разницей больше 1.'
                                }), 400
                
                # Сохраняем данные всех сетов
                for set_data in sets_data:
                    set_number = set_data.get('set_number', 1)
                    score1 = set_data.get('score1', 0)
                    score2 = set_data.get('score2', 0)
                    
                    if set_number == 1:
                        match.set1_score1 = score1
                        match.set1_score2 = score2
                        # Для обратной совместимости сохраняем результаты первого сета
                        match.score1 = score1
                        match.score2 = score2
                    elif set_number == 2:
                        match.set2_score1 = score1
                        match.set2_score2 = score2
                    elif set_number == 3:
                        match.set3_score1 = score1
                        match.set3_score2 = score2
                
                # Определяем статус матча на основе выигранных сетов
                if 'sets_won_1' in data and 'sets_won_2' in data:
                    sets_won_1 = data['sets_won_1']
                    sets_won_2 = data['sets_won_2']
                    
                    # Если счёт 1:1, матч ещё не завершён
                    if sets_won_1 == 1 and sets_won_2 == 1:
                        match.status = 'играют'
                    # Если кто-то выиграл 2 сета, матч завершён
                    elif sets_won_1 >= 2 or sets_won_2 >= 2:
                        match.status = 'завершен'
                    # Если счёт 0:0 или 1:0/0:1, матч в процессе
                    else:
                        match.status = 'играют'
                else:
                    # Если нет данных о выигранных сетах, считаем матч завершённым
                    match.status = 'завершен'
                
                # Начисляем очки участникам матча только если матч завершён
                if match.status == 'завершен':
                    tournament = Tournament.query.get(match.tournament_id)
                    if tournament:
                        # Получаем участников конкретного матча
                        participant1 = Participant.query.get(match.participant1_id)
                        participant2 = Participant.query.get(match.participant2_id)
                        
                        if participant1 and participant2:
                            # Сбрасываем очки участников (убираем старые очки за этот матч)
                            # Это нужно для корректного пересчета при изменении результата
                            participant1.points = (participant1.points or 0)
                            participant2.points = (participant2.points or 0)
                            
                            # Начисляем очки за результат матча
                            if match.winner_id == participant1.id:
                                # Участник 1 победил
                                participant1.points += (tournament.points_win or 1)
                                participant2.points += (tournament.points_loss or 0)
                            elif match.winner_id == participant2.id:
                                # Участник 2 победил
                                participant2.points += (tournament.points_win or 1)
                                participant1.points += (tournament.points_loss or 0)
                            else:
                                # Ничья
                                participant1.points += (tournament.points_draw or 1)
                                participant2.points += (tournament.points_draw or 1)
                            
                            db.session.commit()
                            logger.info(f"Начислены очки за матч {match_id}: участник {participant1.name} = {participant1.points}, участник {participant2.name} = {participant2.points}")
            else:
                # Обратная совместимость со старой структурой
                if 'score1' in data:
                    match.score1 = data['score1']
                if 'score2' in data:
                    match.score2 = data['score2']
                if 'winner_id' in data:
                    match.winner_id = data['winner_id']
                if 'status' in data:
                    match.status = data['status']
                
                # Начисляем очки для старой структуры
                if match.status == 'завершен' and match.winner_id:
                    tournament = Tournament.query.get(match.tournament_id)
                    if tournament:
                        participant1 = Participant.query.get(match.participant1_id)
                        participant2 = Participant.query.get(match.participant2_id)
                        
                        if participant1 and participant2:
                            if match.winner_id == participant1.id:
                                participant1.points = (participant1.points or 0) + (tournament.points_win or 3)
                                participant2.points = (participant2.points or 0) + (tournament.points_loss or 0)
                            elif match.winner_id == participant2.id:
                                participant2.points = (participant2.points or 0) + (tournament.points_win or 3)
                                participant1.points = (participant1.points or 0) + (tournament.points_loss or 0)
                            else:
                                # Ничья
                                participant1.points = (participant1.points or 0) + (tournament.points_draw or 1)
                                participant2.points = (participant2.points or 0) + (tournament.points_draw or 1)
                            
                            db.session.commit()
                            logger.info(f"Начислены очки за матч {match_id} (старая структура)")
            
            match.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Матч {match_id} обновлен")
            return jsonify({'success': True, 'message': 'Матч успешно обновлен'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении матча: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при обновлении матча: {str(e)}'}), 500

    @app.route('/api/matches/<int:match_id>', methods=['DELETE'])
    def delete_match(match_id):
        """Удаление матча"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'error': 'Необходима авторизация'}), 401
        
        # Простая заглушка для админа
        admin = type('Admin', (), {'id': session['admin_id'], 'is_active': True})()
        if not admin or not admin.is_active:
            return jsonify({'error': 'Неверная авторизация'}), 401
        
        match = Match.query.get_or_404(match_id)
        
        # Проверяем права (создатель турнира или системный админ)
        tournament = Tournament.query.get(match.tournament_id)
        if not tournament:
            return jsonify({'error': 'Турнир не найден'}), 404
            
        if admin.id != tournament.admin_id and admin.email != 'admin@system':
            return jsonify({'error': 'Недостаточно прав для удаления матча'}), 403
        
        db.session.delete(match)
        db.session.commit()
        
        logger.info(f"Матч {match_id} удален")
        return jsonify({'success': True, 'message': 'Матч успешно удален'})

    # ===== ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS =====
    
    @app.route('/api/tournaments/<int:tournament_id>/reschedule', methods=['POST'])
    def reschedule_tournament(tournament_id):
        """Пересчет расписания турнира"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        tournament = Tournament.query.get_or_404(tournament_id)
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed: {e}")
            return jsonify({'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'error': 'Необходима авторизация'}), 401
        
        # Простая заглушка для админа
        admin = type('Admin', (), {'id': session['admin_id'], 'is_active': True})()
        if not admin or not admin.is_active:
            return jsonify({'error': 'Неверная авторизация'}), 401
        
        # Проверяем права (создатель турнира)
        if admin.id != tournament.admin_id:
            return jsonify({'error': 'Недостаточно прав'}), 403
        participants = Participant.query.filter_by(tournament_id=tournament_id).all()
        
        if len(participants) < 2:
            return jsonify({'error': 'Недостаточно участников для создания расписания'}), 400
        
        try:
            # Удаляем существующие матчи
            Match.query.filter_by(tournament_id=tournament_id).delete()
            
            # Создаем умное расписание
            matches_created = create_smart_schedule(tournament, participants, Match, db)
            
            db.session.commit()
            
            logger.info(f"Создано {matches_created} матчей для турнира {tournament.name}")
            return jsonify({
                'message': f'Расписание создано: {matches_created} матчей',
                'matches_count': matches_created
            })
        except Exception as e:
            logger.error(f"Ошибка при создании расписания: {str(e)}")
            return jsonify({'error': 'Ошибка при создании расписания'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/debug-chessboard', methods=['POST'])
    @login_required
    def debug_chessboard(tournament_id):
        """Отладка турнирной таблицы"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        tournament = Tournament.query.get_or_404(tournament_id)
        participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
        
        try:
            # Импортируем функцию из routes.main
            from routes.main import debug_chessboard_to_file
            
            success = debug_chessboard_to_file(participants, matches, tournament_id)
            
            if success:
                logger.info(f"Отладочный файл создан для турнира {tournament_id}")
                return jsonify({'success': True, 'message': f'Отладочный файл создан: debug_chessboard_{tournament_id}.txt'})
            else:
                return jsonify({'error': 'Ошибка при создании отладочного файла'}), 500
        except Exception as e:
            logger.error(f"Ошибка при создании отладочного файла: {str(e)}")
            return jsonify({'error': 'Ошибка при создании отладочного файла'}), 500

    # ===== АДМИНИСТРАТИВНЫЕ API МАРШРУТЫ =====
    
    @app.route('/api/admin/users', methods=['GET'])
    def admin_get_users():
        """Получение списка всех пользователей для администратора"""
        from flask import session
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            users = User.query.all()
            users_data = []
            for user in users:
                users_data.append({
                    'id': user.id,
                    'username': user.username,
                    'role': user.role,
                    'created_at': user.created_at.isoformat()
                })
            
            return jsonify({'success': True, 'users': users_data})
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении пользователей'}), 500
    
    @app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
    def admin_delete_user(user_id):
        """Удаление пользователя администратором"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            user = User.query.get_or_404(user_id)
            username = user.username
            
            # Удаляем связанные записи участников
            Participant.query.filter_by(user_id=user_id).delete()
            
            # Удаляем пользователя
            db.session.delete(user)
            db.session.commit()
            
            logger.info(f"Пользователь {username} (ID: {user_id}) удален системным администратором")
            return jsonify({'success': True, 'message': f'Пользователь {username} успешно удален'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении пользователя {user_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении пользователя'}), 500
    
    @app.route('/api/admin/users/batch-delete', methods=['POST'])
    def admin_batch_delete_users():
        """Массовое удаление пользователей"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        data = request.get_json()
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'error': 'Не выбраны пользователи для удаления'}), 400
        
        try:
            deleted_count = 0
            for user_id in user_ids:
                user = User.query.get(user_id)
                if user:
                    # Удаляем связанные записи участников
                    Participant.query.filter_by(user_id=user_id).delete()
                    
                    # Удаляем пользователя
                    db.session.delete(user)
                    deleted_count += 1
            
            db.session.commit()
            
            logger.info(f"Удалено {deleted_count} пользователей системным администратором")
            return jsonify({'success': True, 'message': f'Удалено {deleted_count} пользователей'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при массовом удалении пользователей: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении пользователей'}), 500
    
    @app.route('/api/admin/users/delete-all', methods=['POST'])
    def admin_delete_all_users():
        """Удаление всех пользователей"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            # Удаляем всех участников
            Participant.query.delete()
            
            # Удаляем всех пользователей
            deleted_count = User.query.count()
            User.query.delete()
            
            db.session.commit()
            
            logger.info(f"Удалено {deleted_count} пользователей системным администратором")
            return jsonify({'success': True, 'message': f'Удалено {deleted_count} пользователей'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении всех пользователей: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении всех пользователей'}), 500
    
    @app.route('/api/admin/tournaments', methods=['GET'])
    def admin_get_tournaments():
        """Получение списка всех турниров для администратора"""
        from flask import session
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            tournaments = Tournament.query.all()
            tournaments_data = []
            for tournament in tournaments:
                participant_count = Participant.query.filter_by(tournament_id=tournament.id).count()
                tournaments_data.append({
                    'id': tournament.id,
                    'name': tournament.name,
                    'sport_type': tournament.sport_type,
                    'status': getattr(tournament, 'status', 'активен'),
                    'participant_count': participant_count,
                    'created_at': tournament.created_at.isoformat() if tournament.created_at else None
                })
            
            return jsonify({'success': True, 'tournaments': tournaments_data})
        except Exception as e:
            logger.error(f"Ошибка при получении турниров: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении турниров'}), 500
    
    @app.route('/api/admin/tournaments/batch-delete', methods=['POST'])
    def admin_batch_delete_tournaments():
        """Массовое удаление турниров"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        data = request.get_json()
        tournament_ids = data.get('tournament_ids', [])
        
        if not tournament_ids:
            return jsonify({'success': False, 'error': 'Не выбраны турниры для удаления'}), 400
        
        try:
            deleted_count = 0
            for tournament_id in tournament_ids:
                tournament = Tournament.query.get(tournament_id)
                if tournament:
                    # Удаляем связанные данные
                    Match.query.filter_by(tournament_id=tournament_id).delete()
                    Participant.query.filter_by(tournament_id=tournament_id).delete()
                    
                    # Удаляем турнир
                    db.session.delete(tournament)
                    deleted_count += 1
            
            db.session.commit()
            
            logger.info(f"Удалено {deleted_count} турниров системным администратором")
            return jsonify({'success': True, 'message': f'Удалено {deleted_count} турниров'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при массовом удалении турниров: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении турниров'}), 500
    
    @app.route('/api/admin/tournaments/delete-all', methods=['POST'])
    def admin_delete_all_tournaments():
        """Удаление всех турниров"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            # Удаляем все связанные данные
            Match.query.delete()
            Participant.query.delete()
            
            # Удаляем все турниры
            deleted_count = Tournament.query.count()
            Tournament.query.delete()
            
            db.session.commit()
            
            logger.info(f"Удалено {deleted_count} турниров системным администратором")
            return jsonify({'success': True, 'message': f'Удалено {deleted_count} турниров'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении всех турниров: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении всех турниров'}), 500
    
    @app.route('/api/admin/tournaments/<int:tournament_id>', methods=['PUT'])
    def admin_update_tournament(tournament_id):
        """Обновление турнира администратором"""
        from flask import session
        from flask_wtf.csrf import validate_csrf
        
        # Проверяем CSRF токен
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except:
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_id = session['admin_id']
        admin_email = session.get('admin_email', '')
        
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            
            # Проверяем права доступа
            if admin_email != 'admin@system' and tournament.admin_id != admin_id:
                return jsonify({'success': False, 'error': 'Недостаточно прав для редактирования турнира'}), 403
            
            data = request.get_json()
            
            # Обновляем поля турнира
            if 'name' in data:
                tournament.name = data['name']
            if 'description' in data:
                tournament.description = data['description']
            if 'sport_type' in data:
                tournament.sport_type = data['sport_type']
            if 'start_date' in data and data['start_date']:
                tournament.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            if 'max_participants' in data:
                tournament.max_participants = int(data['max_participants'])
            if 'court_count' in data:
                tournament.court_count = int(data['court_count'])
            if 'match_duration' in data:
                tournament.match_duration = int(data['match_duration'])
            if 'break_duration' in data:
                tournament.break_duration = int(data['break_duration'])
            if 'sets_to_win' in data:
                tournament.sets_to_win = int(data['sets_to_win'])
            if 'points_to_win' in data:
                tournament.points_to_win = int(data['points_to_win'])
            if 'points_win' in data:
                tournament.points_win = int(data['points_win'])
            if 'points_draw' in data:
                tournament.points_draw = int(data['points_draw'])
            if 'points_loss' in data:
                tournament.points_loss = int(data['points_loss'])
            if 'start_time' in data and data['start_time']:
                tournament.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
            if 'end_time' in data and data['end_time']:
                tournament.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
            
            # Обновляем время изменения
            tournament.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Турнир {tournament.name} (ID: {tournament_id}) обновлен администратором {admin_email}")
            return jsonify({'success': True, 'message': 'Турнир успешно обновлен'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении турнира {tournament_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при обновлении турнира'}), 500
    
    @app.route('/api/admin/tournament-admins', methods=['GET'])
    def admin_get_tournament_admins():
        """Получение списка администраторов турниров с их турнирами"""
        from flask import session
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            # Используем уже созданную модель Token из глобального контекста
            # Token уже импортирован в начале файла
            
            # Получаем все турниры с их администраторами
            tournaments = Tournament.query.all()
            
            # Группируем турниры по admin_id
            admins_dict = {}
            for tournament in tournaments:
                admin_id = tournament.admin_id
                if admin_id not in admins_dict:
                    # Создаем информацию об администраторе
                    if admin_id == 1:
                        # Системный администратор
                        admins_dict[admin_id] = {
                            'id': admin_id,
                            'name': 'Системный администратор',
                            'email': 'admin@system',
                            'tournaments': []
                        }
                    else:
                        # Обычный администратор - показываем базовую информацию
                        admins_dict[admin_id] = {
                            'id': admin_id,
                            'name': f'Администратор #{admin_id}',
                            'email': f'admin_{admin_id}@system',
                            'tournaments': []
                        }
                
                # Добавляем турнир к администратору
                admins_dict[admin_id]['tournaments'].append({
                    'id': tournament.id,
                    'name': tournament.name,
                    'sport_type': getattr(tournament, 'sport_type', 'Не указан'),
                    'created_at': tournament.created_at.isoformat() if tournament.created_at else None
                })
            
            # Преобразуем в список
            admins = list(admins_dict.values())
            
            return jsonify({'success': True, 'admins': admins})
        except Exception as e:
            logger.error(f"Ошибка при получении администраторов турниров: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении администраторов турниров'}), 500
    
    @app.route('/api/admin/tournament-participants', methods=['GET'])
    def admin_get_tournament_participants():
        """Получение списка участников турниров с их турнирами"""
        from flask import session
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            # Получаем всех участников с их турнирами
            participants = Participant.query.all()
            
            # Группируем участников по имени
            participants_dict = {}
            for participant in participants:
                name = participant.name
                if name not in participants_dict:
                    participants_dict[name] = {
                        'id': participant.id,
                        'name': participant.name,
                        'is_team': participant.is_team,
                        'tournaments': []
                    }
                
                # Получаем информацию о турнире
                tournament = Tournament.query.get(participant.tournament_id)
                if tournament:
                    participants_dict[name]['tournaments'].append({
                        'id': tournament.id,
                        'name': tournament.name,
                        'sport_type': getattr(tournament, 'sport_type', 'Не указан'),
                        'registered_at': participant.registered_at.isoformat() if participant.registered_at else None
                    })
            
            # Преобразуем в список
            participants_list = list(participants_dict.values())
            
            return jsonify({'success': True, 'participants': participants_list})
        except Exception as e:
            logger.error(f"Ошибка при получении участников турниров: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении участников турниров'}), 500
    
    @app.route('/api/admin/stats', methods=['GET'])
    def admin_get_stats():
        """Получение статистики системы"""
        from flask import session
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            stats = {
                'total_tournaments': Tournament.query.count(),
                'total_users': User.query.count(),
                'total_participants': Participant.query.count(),
                'total_matches': Match.query.count(),
                'active_tournaments': Tournament.query.filter_by(status='активен').count() if hasattr(Tournament, 'status') else Tournament.query.count(),
                'completed_matches': Match.query.filter_by(status='завершен').count()
            }
            
            return jsonify({'success': True, 'stats': stats})
        except Exception as e:
            logger.error(f"Ошибка при получении статистики: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении статистики'}), 500
    
    @app.route('/api/admin/tournament-admins/<int:admin_id>', methods=['DELETE'])
    def admin_delete_tournament_admin(admin_id):
        """Удаление администратора турнира"""
        from flask import session
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        # Нельзя удалить системного администратора
        if admin_id == 1:
            return jsonify({'success': False, 'error': 'Нельзя удалить системного администратора'}), 400
        
        try:
            # Получаем все турниры этого администратора
            tournaments = Tournament.query.filter_by(admin_id=admin_id).all()
            logger.info(f"Найдено турниров для удаления: {len(tournaments)}")
            
            # Удаляем все турниры этого администратора
            for tournament in tournaments:
                logger.info(f"Удаляем турнир: {tournament.name} (ID: {tournament.id})")
                
                # Удаляем всех участников турнира
                participants_deleted = Participant.query.filter_by(tournament_id=tournament.id).delete()
                logger.info(f"Удалено участников: {participants_deleted}")
                
                # Удаляем все матчи турнира
                matches_deleted = Match.query.filter_by(tournament_id=tournament.id).delete()
                logger.info(f"Удалено матчей: {matches_deleted}")
                
                # Удаляем сам турнир
                db.session.delete(tournament)
                logger.info(f"Турнир {tournament.name} помечен для удаления")
            
            # Удаляем токены этого администратора
            tokens_deleted = Token.query.filter_by(email=f'admin_{admin_id}@system').delete()
            logger.info(f"Удалено токенов по email admin_{admin_id}@system: {tokens_deleted}")
            
            # Ищем и удаляем токены по email (если есть другие способы связи)
            all_tokens = Token.query.all()
            additional_tokens_deleted = 0
            for token in all_tokens:
                import hashlib
                if int(hashlib.md5(token.email.encode('utf-8')).hexdigest(), 16) % 1000000 == admin_id:
                    db.session.delete(token)
                    additional_tokens_deleted += 1
            logger.info(f"Удалено дополнительных токенов: {additional_tokens_deleted}")
            
            # Сохраняем изменения
            db.session.commit()
            logger.info(f"Изменения сохранены в базу данных")
            
            logger.info(f"Администратор турнира {admin_id} удален. Удалено турниров: {len(tournaments)}")
            
            return jsonify({
                'success': True, 
                'message': f'Администратор турнира удален. Удалено турниров: {len(tournaments)}'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении администратора турнира {admin_id}: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении администратора турнира'}), 500

    @app.route('/api/join-request', methods=['POST'])
    def join_request():
        """API для отправки заявки на участие в турнире"""
        try:
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.headers.get('X-CSRFToken'))
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            data = request.get_json()
            tournament_id = data.get('tournament_id')
            participant_name = data.get('participant_name', '').strip()
            
            if not tournament_id or not participant_name:
                return jsonify({'success': False, 'error': 'Необходимо указать ID турнира и имя участника'}), 400
            
            # Проверяем существование турнира
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Проверяем, что турнир принимает заявки
            if tournament.status != 'регистрация':
                return jsonify({'success': False, 'error': 'Турнир не принимает заявки на участие'}), 400
            
            # Проверяем, не участвует ли уже участник в турнире
            existing_participant = Participant.query.filter_by(
                tournament_id=tournament_id, 
                name=participant_name
            ).first()
            
            if existing_participant:
                return jsonify({'success': False, 'error': 'Вы уже участвуете в этом турнире'}), 400
            
            # Создаем заявку (пока просто добавляем участника)
            # В будущем здесь можно добавить систему уведомлений для администратора
            new_participant = Participant(
                tournament_id=tournament_id,
                name=participant_name,
                points=0
            )
            
            db.session.add(new_participant)
            db.session.commit()
            
            logger.info(f"Участник {participant_name} подал заявку на турнир {tournament.name} (ID: {tournament_id})")
            
            # Отправляем email администратору турнира
            try:
                # Находим email администратора турнира
                admin_email = None
                if tournament.admin_id == 1:
                    # Системный администратор
                    admin_email = 'admin@system'
                else:
                    # Ищем токен администратора
                    admin_token = Token.query.filter_by(email=f'admin_{tournament.admin_id}@system').first()
                    if not admin_token:
                        # Ищем по admin_id в email
                        all_tokens = Token.query.all()
                        for token in all_tokens:
                            import hashlib
                            if int(hashlib.md5(token.email.encode('utf-8')).hexdigest(), 16) % 1000000 == tournament.admin_id:
                                admin_token = token
                                break
                    
                    if admin_token:
                        admin_email = admin_token.email
                
                if admin_email and admin_email != 'admin@system':
                    # Импортируем функцию отправки email
                    from app import send_email
                    
                    subject = f"Новая заявка на участие в турнире '{tournament.name}'"
                    body = f"{participant_name} добавить в турнир {tournament.name}"
                    
                    if send_email(admin_email, subject, body):
                        logger.info(f"Email уведомление отправлено администратору {admin_email}")
                    else:
                        logger.warning(f"Не удалось отправить email администратору {admin_email}")
                else:
                    logger.warning(f"Не найден email администратора для турнира {tournament.name}")
                    
            except Exception as email_error:
                logger.error(f"Ошибка при отправке email уведомления: {email_error}")
                # Не прерываем выполнение, если email не отправился
            
            return jsonify({
                'success': True, 
                'message': f'Заявка на участие в турнире "{tournament.name}" успешно подана!'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при подаче заявки на участие: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при подаче заявки'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/generate-schedule', methods=['POST'])
    def generate_schedule(tournament_id):
        """API для составления расписания турнира"""
        try:
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.headers.get('X-CSRFToken'))
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Получаем участников турнира
            participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            if len(participants) < 2:
                return jsonify({'success': False, 'error': 'Для составления расписания нужно минимум 2 участника'}), 400
            
            # Удаляем существующие матчи
            existing_matches = Match.query.filter_by(tournament_id=tournament_id).all()
            for match in existing_matches:
                db.session.delete(match)
            
            # Создаем новое расписание
            matches_created = create_smart_schedule(tournament, participants, Match, db)
            
            if matches_created > 0:
                db.session.commit()
                logger.info(f"Расписание составлено для турнира {tournament.name}: создано {matches_created} матчей")
                return jsonify({
                    'success': True, 
                    'message': f'Расписание успешно составлено! Создано {matches_created} матчей.'
                })
            else:
                return jsonify({'success': False, 'error': 'Не удалось создать расписание'}), 500
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при составлении расписания: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при составлении расписания'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/export', methods=['POST'])
    def export_tournament(tournament_id):
        """Экспорт данных турнира в Excel и отправка на email администратора"""
        try:
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.headers.get('X-CSRFToken'))
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Получаем участников турнира
            participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            
            # Получаем матчи турнира
            matches = Match.query.filter_by(tournament_id=tournament_id).all()
            
            # Создаем CSV файл без pandas
            import io
            import csv
            from flask_mail import Mail, Message
            from datetime import datetime
            
            # Создаем CSV файл в памяти
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовок турнира
            writer.writerow(['ТУРНИР'])
            writer.writerow(['Название', tournament.name])
            writer.writerow(['Спорт', tournament.sport_type or 'Теннис'])
            writer.writerow(['Дата начала', tournament.start_date.strftime('%d.%m.%Y') if tournament.start_date else 'Не указана'])
            writer.writerow(['Количество участников', len(participants)])
            writer.writerow(['Количество кортов', tournament.court_count or 4])
            writer.writerow(['Длительность матча (мин)', tournament.match_duration or 15])
            writer.writerow(['Длительность перерыва (мин)', tournament.break_duration or 2])
            writer.writerow([])  # Пустая строка
            
            # Участники
            writer.writerow(['УЧАСТНИКИ'])
            writer.writerow(['Место', 'Участник', 'Игр', 'Побед', 'Поражений', 'Очки'])
            
            for i, participant in enumerate(participants, 1):
                # Подсчитываем статистику участника
                wins = 0
                losses = 0
                points = participant.points or 0
                
                for match in matches:
                    if match.status == 'завершен':
                        if match.participant1_id == participant.id:
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                if match.sets_won_1 > match.sets_won_2:
                                    wins += 1
                                elif match.sets_won_1 < match.sets_won_2:
                                    losses += 1
                        elif match.participant2_id == participant.id:
                            if match.sets_won_1 is not None and match.sets_won_2 is not None:
                                if match.sets_won_1 < match.sets_won_2:
                                    wins += 1
                                elif match.sets_won_1 > match.sets_won_2:
                                    losses += 1
                
                writer.writerow([i, participant.name, wins + losses, wins, losses, points])
            
            writer.writerow([])  # Пустая строка
            
            # Матчи
            writer.writerow(['МАТЧИ'])
            writer.writerow(['Дата', 'Время', 'Корт', 'Участник 1', 'Участник 2', 'Счет', 'Статус', 'Сет 1', 'Сет 2', 'Сет 3'])
            
            for match in matches:
                # Находим участников по ID
                participant1 = next((p for p in participants if p.id == match.participant1_id), None)
                participant2 = next((p for p in participants if p.id == match.participant2_id), None)
                
                writer.writerow([
                    match.match_date.strftime('%d.%m.%Y') if match.match_date else 'Не указана',
                    match.match_time.strftime('%H:%M') if match.match_time else 'Не указано',
                    match.court_number or 'Не указан',
                    participant1.name if participant1 else 'Неизвестно',
                    participant2.name if participant2 else 'Неизвестно',
                    f"{match.sets_won_1}:{match.sets_won_2}" if match.sets_won_1 is not None and match.sets_won_2 is not None else 'Не завершен',
                    match.status,
                    f"{match.set1_score1}:{match.set1_score2}" if match.set1_score1 is not None and match.set1_score2 is not None else '',
                    f"{match.set2_score1}:{match.set2_score2}" if match.set2_score1 is not None and match.set2_score2 is not None else '',
                    f"{match.set3_score1}:{match.set3_score2}" if match.set3_score1 is not None and match.set3_score2 is not None else ''
                ])
            
            # Получаем данные CSV файла
            csv_data = output.getvalue().encode('utf-8')
            
            # Отправляем email с CSV файлом
            try:
                from flask_mail import Message
                
                # Создаем сообщение
                msg = Message(
                    subject=f'Данные турнира "{tournament.name}"',
                    sender=app.config['MAIL_DEFAULT_SENDER'],
                    recipients=['yandvm@yandex.ru'],  # Email администратора турнира
                    body=f'''
Здравствуйте!

Во вложении вы найдете полные данные турнира "{tournament.name}".

Файл содержит:
- Информацию о турнире
- Статистику участников
- Детали всех матчей

Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}

С уважением,
Турнирная система
                    '''
                )
                
                # Прикрепляем CSV файл
                msg.attach(
                    filename=f'tournament_{tournament.name}_{datetime.now().strftime("%Y%m%d_%H%M")}.csv',
                    content_type='text/csv',
                    data=csv_data
                )
                
                # Отправляем письмо (используем глобальный объект mail)
                from flask import current_app
                mail = current_app.extensions['mail']
                mail.send(msg)
                
                logger.info(f"Данные турнира '{tournament.name}' отправлены на email yandvm@yandex.ru")
                
                return jsonify({
                    'success': True,
                    'message': f'Данные турнира "{tournament.name}" успешно отправлены на email администратора!'
                })
                
            except Exception as email_error:
                logger.error(f"Ошибка при отправке email: {email_error}")
                return jsonify({
                    'success': False,
                    'error': f'Ошибка при отправке email: {str(email_error)}'
                }), 500
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте турнира: {e}")
            return jsonify({'success': False, 'error': f'Ошибка при экспорте турнира: {str(e)}'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/add-late-participant', methods=['POST'])
    def add_late_participant(tournament_id):
        """Добавление опоздавшего участника в турнир без пересчета расписания"""
        try:
            # Проверяем CSRF токен
            from flask_wtf.csrf import validate_csrf
            try:
                validate_csrf(request.headers.get('X-CSRFToken'))
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем данные из запроса
            data = request.get_json()
            name = data.get('name', '').strip()
            
            if not name:
                return jsonify({'success': False, 'error': 'Имя участника обязательно'}), 400
            
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Проверяем, не существует ли уже участник с таким именем
            existing_participant = Participant.query.filter_by(
                tournament_id=tournament_id, 
                name=name
            ).first()
            
            if existing_participant:
                return jsonify({'success': False, 'error': 'Участник с таким именем уже существует в турнире'}), 400
            
            # Создаем нового участника
            participant = Participant(
                tournament_id=tournament_id,
                name=name,
                points=0
            )
            
            db.session.add(participant)
            db.session.commit()
            
            logger.info(f"Опоздавший участник '{name}' добавлен в турнир {tournament_id} без пересчета расписания")
            
            return jsonify({
                'success': True,
                'message': f'Участник "{name}" добавлен в турнир. Расписание и результаты матчей сохранены.'
            })
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении опоздавшего участника: {e}")
            return jsonify({'success': False, 'error': f'Ошибка при добавлении участника: {str(e)}'}), 500

    # ===== ОТЛАДОЧНЫЕ API МАРШРУТЫ =====
    
    @app.route('/api/debug/tokens', methods=['GET'])
    def debug_get_tokens():
        """Получение списка выданных токенов для отладки"""
        try:
            # Читаем токены из файла tokens.txt
            tokens = []
            try:
                with open('tokens.txt', 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line and ' - ' in line:
                            parts = line.split(' - ')
                            if len(parts) >= 4:
                                timestamp = parts[0]
                                email = parts[1]
                                name = parts[2]
                                token_part = parts[3].replace('Токен: ', '')
                                
                                # Проверяем, был ли отправлен email
                                email_sent = 'EMAIL НЕ ОТПРАВЛЕН' not in line
                                
                                tokens.append({
                                    'timestamp': timestamp,
                                    'email': email,
                                    'name': name,
                                    'token': token_part,
                                    'email_sent': email_sent
                                })
            except FileNotFoundError:
                logger.info("Файл tokens.txt не найден")
            except Exception as e:
                logger.error(f"Ошибка чтения файла tokens.txt: {e}")
            
            # Сортируем по времени (новые сверху)
            tokens.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return jsonify({
                'success': True,
                'tokens': tokens
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении отладочных токенов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении токенов'}), 500

    @app.route('/api/debug/test-email', methods=['POST'])
    def debug_test_email():
        """Тестирование отправки email для отладки"""
        try:
            data = request.get_json()
            test_email = data.get('email', 'test@example.com')
            
            # Импортируем функцию отправки email
            from routes.main import send_token_email
            
            logger.info(f"Тестирование отправки email на {test_email}")
            result = send_token_email(test_email, 'Тестовый пользователь', '99')
            
            return jsonify({
                'success': True,
                'email_sent': result,
                'message': 'Email отправлен успешно' if result else 'Ошибка отправки email'
            })
            
        except Exception as e:
            logger.error(f"Ошибка тестирования email: {e}")
            return jsonify({'success': False, 'error': f'Ошибка тестирования: {str(e)}'}), 500