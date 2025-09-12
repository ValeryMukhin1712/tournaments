"""
API маршруты приложения
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date, time
import logging

logger = logging.getLogger(__name__)

def create_api_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog):
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
            return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400
        
        try:
            # Создаем нового пользователя
            user = User(
                username=data['username'],
                password_hash=generate_password_hash(data['password']),
                role=data.get('role', 'участник')
            )
            db.session.add(user)
            db.session.commit()
            
            logger.info(f"Создан новый пользователь: {data['username']} (ID: {user.id})")
            return jsonify({
                'message': 'Пользователь успешно создан',
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
        return jsonify({'message': 'Роль успешно изменена'})

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
        
        logger.info(f"Пользователь {username} удален")
        return jsonify({'message': 'Пользователь успешно удален'})

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
    @login_required
    def get_match(match_id):
        """Получение информации о матче"""
        match = Match.query.get_or_404(match_id)
        
        return jsonify({
            'success': True,
            'match': {
                'id': match.id,
                'tournament_id': match.tournament_id,
                'participant1_id': match.participant1_id,
                'participant2_id': match.participant2_id,
                'score1': match.score1,
                'score2': match.score2,
                'winner_id': match.winner_id,
                'match_date': match.match_date.isoformat() if match.match_date else None,
                'match_time': match.match_time.isoformat() if match.match_time else None,
                'court_number': match.court_number,
                'match_number': match.match_number,
                'status': match.status,
                'created_at': match.created_at.isoformat(),
                'updated_at': match.updated_at.isoformat()
            }
        })

    # ===== ТУРНИРЫ (дополнительные маршруты) =====
    
    @app.route('/api/tournaments/<int:tournament_id>/participants', methods=['POST'])
    def add_participant(tournament_id):
        """Добавление участника в турнир"""
        tournament = Tournament.query.get_or_404(tournament_id)
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Необходимо имя участника'}), 400
        
        # Проверяем дубликаты
        existing_participant = Participant.query.filter_by(
            tournament_id=tournament_id,
            name=data['name']
        ).first()
        
        if existing_participant:
            return jsonify({'error': f'Участник с именем "{data["name"]}" уже существует в турнире'}), 400
        
        # Если указан user_id, проверяем, что пользователь не участвует в турнире
        if data.get('user_id'):
            existing_user_participant = Participant.query.filter_by(
                tournament_id=tournament_id,
                user_id=data['user_id']
            ).first()
            
            if existing_user_participant:
                return jsonify({'error': f'Пользователь уже участвует в турнире'}), 400
        
        try:
            participant = Participant(
                tournament_id=tournament_id,
                name=data['name'],
                is_team=data.get('is_team', False),
                user_id=data.get('user_id')
            )
            db.session.add(participant)
            db.session.commit()
            
            logger.info(f"Добавлен участник {data['name']} в турнир {tournament.name}")
            return jsonify({
                'message': 'Участник успешно добавлен',
                'participant': {
                    'id': participant.id,
                    'name': participant.name,
                    'is_team': participant.is_team
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении участника: {str(e)}")
            return jsonify({'error': 'Ошибка при добавлении участника'}), 500

    @app.route('/api/tournaments/<int:tournament_id>', methods=['DELETE'])
    @login_required
    def delete_tournament(tournament_id):
        """Удаление турнира"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        tournament = Tournament.query.get_or_404(tournament_id)
        tournament_name = tournament.name
        
        # Удаляем связанные данные
        Participant.query.filter_by(tournament_id=tournament_id).delete()
        Match.query.filter_by(tournament_id=tournament_id).delete()
        
        db.session.delete(tournament)
        db.session.commit()
        
        logger.info(f"Турнир {tournament_name} удален")
        return jsonify({'message': 'Турнир успешно удален'})

    @app.route('/api/tournaments/<int:tournament_id>/participants/<int:participant_id>', methods=['DELETE'])
    @login_required
    def delete_participant(tournament_id, participant_id):
        """Удаление участника из турнира"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        try:
            participant = Participant.query.filter_by(
                id=participant_id, 
                tournament_id=tournament_id
            ).first_or_404()
            
            participant_name = participant.name
            
            # Удаляем все матчи, в которых участвует этот участник
            matches_to_delete = Match.query.filter(
                (Match.participant1_id == participant_id) | 
                (Match.participant2_id == participant_id)
            ).all()
            
            for match in matches_to_delete:
                db.session.delete(match)
            
            # Удаляем самого участника
            db.session.delete(participant)
            db.session.commit()
            
            logger.info(f"Участник {participant_name} и {len(matches_to_delete)} связанных матчей удалены из турнира {tournament_id}")
            return jsonify({'message': 'Участник успешно удален'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении участника: {str(e)}")
            return jsonify({'error': 'Ошибка при удалении участника'}), 500

    # ===== МАТЧИ (дополнительные маршруты) =====
    
    @app.route('/api/matches', methods=['POST'])
    @login_required
    def create_match():
        """Создание нового матча"""
        data = request.get_json()
        if not data or not data.get('tournament_id'):
            return jsonify({'error': 'Необходим ID турнира'}), 400
        
        try:
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
            db.session.add(match)
            db.session.commit()
            
            logger.info(f"Создан матч {match.id} в турнире {data['tournament_id']}")
            return jsonify({
                'message': 'Матч успешно создан',
                'match': {
                    'id': match.id,
                    'tournament_id': match.tournament_id,
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при создании матча: {str(e)}")
            return jsonify({'error': 'Ошибка при создании матча'}), 500

    @app.route('/api/matches/<int:match_id>', methods=['PUT'])
    @login_required
    def update_match(match_id):
        """Обновление матча"""
        match = Match.query.get_or_404(match_id)
        data = request.get_json()
        
        try:
            # Обработка новой структуры с сетами
            if 'sets' in data and data['sets']:
                sets_data = data['sets']
                # Берем результаты из первого сета для обратной совместимости
                if len(sets_data) > 0:
                    first_set = sets_data[0]
                    match.score1 = first_set.get('score1', 0)
                    match.score2 = first_set.get('score2', 0)
                    
                    # Определяем победителя
                    if match.score1 > match.score2:
                        match.winner_id = match.participant1_id
                    elif match.score2 > match.score1:
                        match.winner_id = match.participant2_id
                    else:
                        match.winner_id = None  # Ничья
                    
                    match.status = 'завершен'
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
            
            match.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Матч {match_id} обновлен")
            return jsonify({'success': True, 'message': 'Матч успешно обновлен'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении матча: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при обновлении матча: {str(e)}'}), 500

    @app.route('/api/matches/<int:match_id>', methods=['DELETE'])
    @login_required
    def delete_match(match_id):
        """Удаление матча"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        match = Match.query.get_or_404(match_id)
        db.session.delete(match)
        db.session.commit()
        
        logger.info(f"Матч {match_id} удален")
        return jsonify({'message': 'Матч успешно удален'})

    # ===== ДОПОЛНИТЕЛЬНЫЕ ENDPOINTS =====
    
    @app.route('/api/tournaments/<int:tournament_id>/reschedule', methods=['POST'])
    @login_required
    def reschedule_tournament(tournament_id):
        """Пересчет расписания турнира"""
        if current_user.role != 'администратор':
            return jsonify({'error': 'Недостаточно прав'}), 403
        
        tournament = Tournament.query.get_or_404(tournament_id)
        participants = Participant.query.filter_by(tournament_id=tournament_id).all()
        
        if len(participants) < 2:
            return jsonify({'error': 'Недостаточно участников для создания расписания'}), 400
        
        try:
            # Импортируем функцию генерации расписания
            from routes.main import generate_tournament_schedule
            
            # Генерируем новое расписание
            matches = generate_tournament_schedule(participants, tournament, db, Match)
            
            logger.info(f"Создано {len(matches)} матчей для турнира {tournament.name}")
            return jsonify({
                'message': f'Расписание создано: {len(matches)} матчей',
                'matches_count': len(matches)
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
                return jsonify({'message': f'Отладочный файл создан: debug_chessboard_{tournament_id}.txt'})
            else:
                return jsonify({'error': 'Ошибка при создании отладочного файла'}), 500
        except Exception as e:
            logger.error(f"Ошибка при создании отладочного файла: {str(e)}")
            return jsonify({'error': 'Ошибка при создании отладочного файла'}), 500
