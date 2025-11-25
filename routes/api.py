"""
API маршруты приложения
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date, time
import logging
from flask_wtf.csrf import CSRFProtect
from routes.main import update_tournament_status
from utils.telegram_utils import send_telegram_message
from utils.qr_generator import generate_telegram_token, generate_qr_code, get_bot_username

logger = logging.getLogger(__name__)

def recalculate_schedule_after_match_completion(match_id, Tournament, Match, db):
    """
    Пересчитывает время начала следующих матчей на той же площадке после завершения матча.
    Учитывает реальное время окончания матча.
    
    Args:
        match_id: ID завершенного матча
        Tournament: Модель турнира
        Match: Модель матча
        db: Объект базы данных
    """
    from datetime import datetime, timedelta
    
    try:
        logger.info(f"[ПЕРЕСЧЕТ] >>> ВХОД В ФУНКЦИЮ для матча {match_id}")
        completed_match = Match.query.get(match_id)
        if not completed_match:
            logger.warning(f"[ПЕРЕСЧЕТ] Матч {match_id} не найден для пересчета расписания")
            return
        
        logger.info(f"[ПЕРЕСЧЕТ] Матч {match_id} найден: статус={completed_match.status}, площадка={completed_match.court_number}, match_number={completed_match.match_number}")
        
        # Работаем только с завершенными матчами
        if completed_match.status != 'завершен':
            logger.info(f"[ПЕРЕСЧЕТ] Матч {match_id} не завершен (статус: {completed_match.status}), пересчет не требуется")
            return
        
        # Всегда используем текущее локальное время как время окончания последнего завершенного матча
        # Это позволяет пересчитывать время следующих матчей от момента сохранения
        # Используем datetime.now() вместо datetime.utcnow() для учета локального часового пояса
        match_end_time = datetime.now()
        
        logger.info(f"[ПЕРЕСЧЕТ] Начало пересчета для матча {match_id} (площадка: {completed_match.court_number}, match_number: {completed_match.match_number})")
        logger.info(f"[ПЕРЕСЧЕТ] Локальное время окончания матча: {match_end_time}")
        
        # Сохраняем текущее время в actual_end_time, если оно еще не установлено
        if not completed_match.actual_end_time:
            completed_match.actual_end_time = match_end_time
            db.session.commit()
        
        # Получаем турнир для параметров
        tournament = Tournament.query.get(completed_match.tournament_id)
        if not tournament:
            logger.warning(f"Турнир {completed_match.tournament_id} не найден")
            return
        
        match_duration = tournament.match_duration or 15  # длительность матча в минутах
        break_duration = tournament.break_duration or 2   # перерыв между матчами в минутах
        end_time = tournament.end_time or None  # конец рабочего дня
        
        logger.info(f"[ПЕРЕСЧЕТ] Параметры турнира: длительность={match_duration} мин, перерыв={break_duration} мин")
        
        # Находим следующий матч на той же площадке после этого матча
        # Используем match_number для правильного определения порядка
        # Ищем следующий матч с большим match_number на той же площадке
        next_match = Match.query.filter(
            Match.tournament_id == completed_match.tournament_id,
            Match.court_number == completed_match.court_number,
            Match.id != match_id,
            Match.status != 'завершен',
            Match.match_number > completed_match.match_number
        ).order_by(
            Match.match_number.asc()
        ).first()
        
        # Если не нашли по match_number, пробуем найти по дате и времени (для обратной совместимости)
        if not next_match:
            logger.info(f"[ПЕРЕСЧЕТ] Не найден следующий матч по match_number, пробуем по дате/времени")
            next_match = Match.query.filter(
                Match.tournament_id == completed_match.tournament_id,
                Match.court_number == completed_match.court_number,
                Match.id != match_id,
                Match.status != 'завершен'
            ).order_by(
                Match.match_date.asc(),
                Match.match_time.asc(),
                Match.match_number.asc()
            ).first()
        
        # Если всё ещё не нашли, пробуем найти любой незавершенный матч на той же площадке
        if not next_match:
            logger.info(f"[ПЕРЕСЧЕТ] Не найден следующий матч по дате/времени, пробуем любой незавершенный на площадке")
            all_court_matches = Match.query.filter(
                Match.tournament_id == completed_match.tournament_id,
                Match.court_number == completed_match.court_number,
                Match.id != match_id,
                Match.status != 'завершен'
            ).all()
            logger.info(f"[ПЕРЕСЧЕТ] Найдено незавершенных матчей на площадке {completed_match.court_number}: {len(all_court_matches)}")
            for m in all_court_matches:
                logger.info(f"[ПЕРЕСЧЕТ]   - Матч ID={m.id}, match_number={m.match_number}, статус={m.status}, время={m.match_date} {m.match_time}")
            
            # Берём первый незавершенный матч на площадке после текущего по match_number или ID
            next_match = Match.query.filter(
                Match.tournament_id == completed_match.tournament_id,
                Match.court_number == completed_match.court_number,
                Match.id != match_id,
                Match.status != 'завершен'
            ).order_by(
                Match.id.asc()
            ).first()
        
        if not next_match:
            logger.info(f"[ПЕРЕСЧЕТ] Нет следующих матчей на площадке {completed_match.court_number} после матча {match_id}")
            return
        
        logger.info(f"[ПЕРЕСЧЕТ] Найден следующий матч: ID={next_match.id}, match_number={next_match.match_number}, текущее время={next_match.match_date} {next_match.match_time}")
        
        # Вычисляем новое время начала следующего матча
        # Время окончания предыдущего матча + перерыв
        # При динамическом пересчете используем реальное время окончания без ограничений рабочего дня
        new_start_time = match_end_time + timedelta(minutes=break_duration)
        
        # Берем дату и время напрямую из вычисленного времени
        # При динамическом пересчете не ограничиваемся рабочим временем,
        # так как матч уже начался и должен быть завершен независимо от расписания
        new_start_date = new_start_time.date()
        new_start_time_only = new_start_time.time()
        
        logger.info(f"[ПЕРЕСЧЕТ] Вычислено новое время начала: {new_start_date} {new_start_time_only} (от {match_end_time})")
        
        # Обновляем запланированное время следующего матча
        old_time = next_match.match_time
        old_date = next_match.match_date
        
        next_match.match_time = new_start_time_only
        next_match.match_date = new_start_date
        
        # Устанавливаем реальное время начала, если матч еще не начался
        if not next_match.actual_start_time and next_match.status == 'запланирован':
            # Реальное время начала = запланированное (будет обновлено при фактическом начале)
            next_match.actual_start_time = datetime.combine(new_start_date, new_start_time_only)
        
        logger.info(
            f"[ПЕРЕСЧЕТ] Матч {next_match.id} на площадке {completed_match.court_number}: "
            f"{old_date} {old_time} -> {new_start_date} {new_start_time_only}"
        )
        
        # Проверяем, что изменения сохранились
        db.session.commit()
        db.session.refresh(next_match)
        
        # Убеждаемся, что дата и время правильно сохранены
        logger.info(f"[ПЕРЕСЧЕТ] После commit: матч {next_match.id} теперь имеет время {next_match.match_date} {next_match.match_time}")
        logger.info(f"[ПЕРЕСЧЕТ] Проверка: match_date type={type(next_match.match_date)}, match_time type={type(next_match.match_time)}")
        
        # Дополнительная проверка через прямой запрос из базы
        verify_match = Match.query.get(next_match.id)
        if verify_match:
            logger.info(f"[ПЕРЕСЧЕТ] Прямой запрос из БД: match_date={verify_match.match_date}, match_time={verify_match.match_time}")
        
        # КАСКАДНЫЙ ПЕРЕСЧЕТ: обновляем ВСЕ последующие матчи на этой площадке по цепочке
        current_planned_end = datetime.combine(new_start_date, new_start_time_only) + timedelta(minutes=match_duration)
        cursor_match = next_match
        while True:
            following = Match.query.filter(
                Match.tournament_id == completed_match.tournament_id,
                Match.court_number == completed_match.court_number,
                Match.id != match_id,
                Match.id != cursor_match.id,
                Match.status != 'завершен',
                Match.match_number > cursor_match.match_number
            ).order_by(Match.match_number.asc()).first()
            if not following:
                break
            new_start = current_planned_end + timedelta(minutes=break_duration)
            new_date = new_start.date()
            new_time_only = new_start.time()
            old_date = following.match_date
            old_time = following.match_time
            following.match_date = new_date
            following.match_time = new_time_only
            logger.info(
                f"[ПЕРЕСЧЕТ КАСКАДНЫЙ] Матч {following.id}: {old_date} {old_time} -> {new_date} {new_time_only}"
            )
            db.session.commit()
            # следующий шаг рассчитываем от конца только что сдвинутого following
            current_planned_end = datetime.combine(new_date, new_time_only) + timedelta(minutes=match_duration)
            cursor_match = following
    
    except Exception as e:
        logger.error(f"[ОШИБКА ПЕРЕСЧЕТА] Матч {match_id}: {e}")
        db.session.rollback()


def create_smart_schedule(tournament, participants, Match, db, preserve_results=True):
    """
    Создает расписание матчей для кругового турнира по правильному алгоритму
    с возможностью сохранения результатов существующих матчей
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
    
    logger.info(f"Создание расписания для {n} участников: {[p.name for p in participants]}")
    
    # Сохраняем результаты существующих матчей, если нужно
    existing_results = {}
    if preserve_results:
        existing_matches = Match.query.filter_by(tournament_id=tournament.id).all()
        for match in existing_matches:
            if match.status in ['завершен', 'в процессе', 'играют']:
                key = tuple(sorted([match.participant1_id, match.participant2_id]))
                existing_results[key] = {
                    'status': match.status,
                    'sets_won_1': match.sets_won_1,
                    'sets_won_2': match.sets_won_2,
                    'set1_score1': match.set1_score1,
                    'set1_score2': match.set1_score2,
                    'set2_score1': match.set2_score1,
                    'set2_score2': match.set2_score2,
                    'set3_score1': match.set3_score1,
                    'set3_score2': match.set3_score2,
                    'winner_id': match.winner_id,
                    'score1': match.score1,
                    'score2': match.score2
                }
        logger.info(f"Сохранено {len(existing_results)} результатов существующих матчей")
    
    # Удаляем все существующие матчи перед созданием новых
    # Используем raw SQL для полного контроля над операциями
    from models.match_log import MatchLog
    from sqlalchemy import text
    
    # Получаем ID матчей для удаления
    existing_matches = Match.query.filter_by(tournament_id=tournament.id).all()
    match_ids = [match.id for match in existing_matches]
    
    # Полностью очищаем match_log для этого турнира через raw SQL
    if match_ids:
        db.session.execute(text("DELETE FROM match_log WHERE match_id IN :match_ids"), 
                          {"match_ids": match_ids})
        logger.info(f"Очищены все записи match_log для {len(match_ids)} матчей турнира {tournament.id}")
    
    # Удаляем матчи через raw SQL
    if match_ids:
        db.session.execute(text("DELETE FROM match WHERE id IN :match_ids"), 
                          {"match_ids": match_ids})
        logger.info(f"Удалено {len(match_ids)} существующих матчей через raw SQL")
    
    # Коммитим удаление, чтобы избежать проблем с autoflush
    db.session.commit()
    
    # Создаем круговое расписание по правильному алгоритму
    rounds = create_round_robin_schedule(participants)
    
    logger.info(f"Создано {len(rounds)} туров для {len(participants)} участников")
    for i, round_matches in enumerate(rounds, 1):
        logger.info(f"Тур {i}: {[f'{m[0].name} vs {m[1].name}' for m in round_matches]}")
    
    # Проверяем на дубликаты
    all_matches = []
    for round_matches in rounds:
        for match in round_matches:
            participant1, participant2 = match
            key = tuple(sorted([participant1.id, participant2.id]))
            if key in all_matches:
                logger.error(f"ДУБЛИКАТ МАТЧА: {participant1.name} vs {participant2.name}")
            else:
                all_matches.append(key)
    logger.info(f"Всего уникальных матчей: {len(all_matches)}")
    
    # Распределяем матчи по времени и площадкам
    scheduled_matches = []
    global_match_number = 1  # Глобальная нумерация матчей
    current_time = start_time
    current_date = start_date
    
    # Сначала размещаем завершенные матчи в начале расписания
    completed_matches = []
    pending_matches = []
    
    for round_num, round_matches in enumerate(rounds, 1):
        for match in round_matches:
            participant1, participant2 = match
            key = tuple(sorted([participant1.id, participant2.id]))
            
            if key in existing_results:
                completed_matches.append((match, existing_results[key]))
            else:
                pending_matches.append(match)
    
    # Размещаем завершенные матчи в начале
    for match, result_data in completed_matches:
        participant1, participant2 = match
        p1_id, p2_id = participant1.id, participant2.id
        
        logger.info(f"Восстановление завершенного матча: {participant1.name} vs {participant2.name} (номер {global_match_number})")
        
        # Создаем матч с сохраненными результатами
        match_obj = Match(
            tournament_id=tournament.id,
            participant1_id=p1_id,
            participant2_id=p2_id,
            status=result_data['status'],
            match_date=current_date,
            match_time=current_time,
            court_number=1,  # Завершенные матчи на первой площадке
            match_number=global_match_number,
            sets_won_1=result_data['sets_won_1'],
            sets_won_2=result_data['sets_won_2'],
            set1_score1=result_data['set1_score1'],
            set1_score2=result_data['set1_score2'],
            set2_score1=result_data['set2_score1'],
            set2_score2=result_data['set2_score2'],
            set3_score1=result_data['set3_score1'],
            set3_score2=result_data['set3_score2'],
            winner_id=result_data['winner_id'],
            score1=result_data['score1'],
            score2=result_data['score2']
        )
        db.session.add(match_obj)
        scheduled_matches.append(match_obj)
        global_match_number += 1
        
        # Переходим к следующему времени
        current_time = add_minutes_to_time(current_time, time_match + time_break)
        if current_time > end_time:
            current_date += timedelta(days=1)
            current_time = start_time
    
    # Теперь размещаем оставшиеся матчи
    rounds_remaining = []
    completed_match_keys = set()
    for match, _ in completed_matches:
        participant1, participant2 = match
        key = tuple(sorted([participant1.id, participant2.id]))
        completed_match_keys.add(key)
    
    for round_num, round_matches in enumerate(rounds, 1):
        remaining_in_round = []
        for match in round_matches:
            participant1, participant2 = match
            key = tuple(sorted([participant1.id, participant2.id]))
            if key not in completed_match_keys:
                remaining_in_round.append(match)
        if remaining_in_round:
            rounds_remaining.append(remaining_in_round)
    
    for round_num, round_matches in enumerate(rounds_remaining, 1):
        logger.info(f"Тур {round_num}: {len(round_matches)} матчей")
        
        # Распределяем матчи тура по площадкам
        court_assignments = distribute_matches_to_courts(round_matches, k)
        
        # Создаем матчи для текущего тура
        round_matches_created = []
        for court_num, court_matches in court_assignments.items():
            for match in court_matches:
                participant1, participant2 = match
                p1_id, p2_id = participant1.id, participant2.id
                
                logger.info(f"Создание нового матча: {participant1.name} vs {participant2.name} (площадка {court_num}, номер {global_match_number})")
                
                # Создаем матч
                match_obj = Match(
                    tournament_id=tournament.id,
                    participant1_id=p1_id,
                    participant2_id=p2_id,
                    status='запланирован',
                    match_date=current_date,
                    match_time=current_time,
                    court_number=court_num,
                    match_number=global_match_number
                )
                db.session.add(match_obj)
                scheduled_matches.append(match_obj)
                round_matches_created.append(match_obj)
                global_match_number += 1
        
        # Сортируем матчи тура по номеру площадки для правильной нумерации
        round_matches_created.sort(key=lambda m: m.court_number)
        
        # Переназначаем номера матчей в туре (используем правильную нумерацию)
        for i, match in enumerate(round_matches_created):
            match.match_number = global_match_number - len(round_matches_created) + i
            logger.info(f"Матч {match.participant1_id} vs {match.participant2_id} получил номер {match.match_number}")
        
        # Переходим к следующему времени
        current_time = add_minutes_to_time(current_time, time_match + time_break)
        
        # Если время выходит за пределы рабочего дня, переходим на следующий день
        if current_time > end_time:
            current_date += timedelta(days=1)
            current_time = start_time
    
    return len(scheduled_matches)


def create_round_robin_schedule(participants):
    """
    Создает круговое расписание по правильному алгоритму
    """
    n = len(participants)
    logger.info(f"create_round_robin_schedule: получено {n} участников: {[p.name for p in participants]}")
    if n < 2:
        return []
    
    # Если нечетное количество участников, добавляем "bye" (пустую команду)
    if n % 2 == 1:
        bye_participant = type('ByeParticipant', (), {'id': -1, 'name': 'BYE'})()
        participants = participants + [bye_participant]
        n += 1
    
    # Создаем список участников
    players = list(range(n))
    rounds = []
    
    # Количество туров = n - 1
    for round_num in range(n - 1):
        round_matches = []
        
        # Создаем пары для текущего тура
        for i in range(n // 2):
            # Первая пара: первый участник с последним
            if i == 0:
                player1 = players[0]
                player2 = players[n - 1]
            else:
                # Остальные пары по круговому принципу
                player1 = players[i]
                player2 = players[n - 1 - i]
            
            # Пропускаем матчи с "bye" (фейковым участником)
            if participants[player1].id != -1 and participants[player2].id != -1:
                round_matches.append((participants[player1], participants[player2]))
        
        rounds.append(round_matches)
        
        # Сдвигаем участников для следующего тура (кроме первого)
        # Последний участник становится вторым, остальные сдвигаются
        players = [players[0]] + [players[-1]] + players[1:-1]
    
    return rounds


def distribute_matches_to_courts(round_matches, num_courts):
    """
    Распределяет матчи тура по площадкам
    """
    court_assignments = {i: [] for i in range(1, num_courts + 1)}
    
    for i, match in enumerate(round_matches):
        court_num = (i % num_courts) + 1
        court_assignments[court_num].append(match)
    
    return court_assignments


def add_minutes_to_time(time_obj, minutes):
    """Добавляет минуты к времени"""
    from datetime import datetime, timedelta
    dt = datetime.combine(date.today(), time_obj)
    new_dt = dt + timedelta(minutes=minutes)
    return new_dt.time()

def create_api_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, Token, WaitingList, Settings, Player, Rally):
    """Создает API маршруты приложения"""
    
    # Получаем объект CSRF из приложения
    csrf = app.extensions.get('csrf')
    if not csrf:
        # Если CSRF не найден, создаем заглушку
        class CSRFStub:
            def exempt(self, f):
                return f
        csrf = CSRFStub()
    
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
        
        # Проверяем, что турнир с таким именем не существует
        existing_tournament = Tournament.query.filter_by(name=data['name']).first()
        if existing_tournament:
            return jsonify({'error': f'⚠️ Турнир с названием "{data["name"]}" уже существует в системе. Пожалуйста, выберите другое уникальное название.'}), 400
        
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
            
        if admin.id != tournament.admin_id and session.get('admin_email') != 'admin@system':
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
                user_id=data.get('user_id'),
                registered_at=tournament.created_at  # Устанавливаем время регистрации как время создания турнира
            )
            db.session.add(participant)
            
            # Автоматически добавляем игрока в список игроков
            player_name = data['name'].strip()
            existing_player = Player.query.filter_by(name=player_name).first()
            if not existing_player:
                new_player = Player(name=player_name)
                db.session.add(new_player)
                logger.info(f"Игрок '{player_name}' добавлен в список игроков")
            else:
                # Обновляем время последнего использования
                existing_player.last_used_at = datetime.utcnow()
                logger.info(f"Время последнего использования игрока '{player_name}' обновлено")
            
            db.session.commit()
            
            # Автоматически создаем расписание после добавления участника
            participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            if len(participants) >= 2:  # Минимум 2 участника для создания расписания
                # Удаляем существующие матчи перед созданием новых
                existing_matches = Match.query.filter_by(tournament_id=tournament_id).all()
                for match in existing_matches:
                    db.session.delete(match)
                
                # Создаем новое расписание с сохранением результатов
                matches_created = create_smart_schedule(tournament, participants, Match, db, preserve_results=True)
                db.session.commit()
                
                logger.info(f"Автоматически пересоздано {matches_created} матчей для турнира {tournament_id} (удалено {len(existing_matches)} старых матчей)")
            
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
        if admin.id != tournament.admin_id and session.get('admin_email') != 'admin@system':
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
            
            # Пересоздаем расписание для оставшихся участников
            remaining_participants = Participant.query.filter_by(tournament_id=tournament_id).all()
            if len(remaining_participants) >= 2:
                # Удаляем все оставшиеся матчи
                all_matches = Match.query.filter_by(tournament_id=tournament_id).all()
                for match in all_matches:
                    db.session.delete(match)
                
                # Создаем новое расписание
                matches_created = create_smart_schedule(tournament, remaining_participants, Match, db, preserve_results=True)
                db.session.commit()
                
                logger.info(f"Участник '{participant_name}' удален из турнира {tournament_id}. Пересоздано {matches_created} матчей для {len(remaining_participants)} оставшихся участников.")
            else:
                logger.info(f"Участник '{participant_name}' удален из турнира {tournament_id}. Осталось {len(remaining_participants)} участников - расписание не создается.")
            
            return jsonify({'success': True, 'message': f'Участник "{participant_name}" успешно удален. Расписание обновлено.'}), 200
            
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
        if admin.id != tournament.admin_id and session.get('admin_email') != 'admin@system':
            return jsonify({'error': 'Недостаточно прав для удаления турнира'}), 403
        
        try:
            # Удаляем все связанные данные
            # 1. Удаляем записи журнала матчей
            from models.match_log import MatchLog
            MatchLog.query.filter_by(tournament_id=tournament_id).delete()
            
            # 2. Удаляем матчи
            Match.query.filter_by(tournament_id=tournament_id).delete()
            
            # 3. Удаляем участников
            Participant.query.filter_by(tournament_id=tournament_id).delete()
            
            # 4. Удаляем турнир
            tournament_name = tournament.name
            db.session.delete(tournament)
            
            db.session.commit()
            
            logger.info(f"Турнир '{tournament_name}' (ID: {tournament_id}) удален админом {admin_email}")
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
        from datetime import datetime
        
        logger.info(f"[update_match] Вызов update_match для матча {match_id}")
        data = request.get_json()
        logger.info(f"[update_match] Получены данные: {data}")
        
        # Проверяем CSRF токен
        csrf_token = request.headers.get('X-CSRFToken')
        logger.info(f"[update_match] CSRF токен: {csrf_token}")
        try:
            validate_csrf(csrf_token)
            logger.info("[update_match] CSRF токен валиден")
        except Exception as e:
            logger.warning(f"[update_match] CSRF validation failed: {e}")
            return jsonify({'error': 'Неверный CSRF токен'}), 400
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            logger.warning(f"[update_match] Нет авторизации для матча {match_id}")
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
            
        if admin.id != tournament.admin_id and session.get('admin_email') != 'admin@system':
            return jsonify({'error': 'Недостаточно прав для изменения матча'}), 403
        
        data = request.get_json()
        logger.info(f"Обновление матча {match_id}: получены данные: {data}")
        
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
                    
                    # Определяем победителя матча (нужно выиграть 2 сета)
                    sets_to_win = tournament.sets_to_win if tournament else 2
                    
                    if sets_won_1 >= sets_to_win:
                        match.winner_id = match.participant1_id
                    elif sets_won_2 >= sets_to_win:
                        match.winner_id = match.participant2_id
                    else:
                        match.winner_id = None  # Матч не завершен
                
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
                        
                        # Проверяем разницу в 2 очка только если у проигравшего очков больше или равно ("очков для победы" - 1)
                        loser_score = min(score1, score2)
                        winner_score = max(score1, score2)
                        
                        # Специальное правило: если оба участника набрали "очков для победы", то это равный счет (например, 11:11)
                        if score1 == points_to_win and score2 == points_to_win:
                            # Равный счет разрешен, но не будет отображаться в таблице
                            print(f"Равный счет {score1}:{score2} разрешен, но не будет отображаться в таблице")
                        elif (score1 == points_to_win and score2 == (points_to_win - 1)) or (score2 == points_to_win and score1 == (points_to_win - 1)):
                            # Специальное правило: если один участник набрал "очков для победы", а другой на 1 меньше, то сет продолжается (например, 11:10)
                            print(f"Счет {score1}:{score2} разрешен - сет продолжается (один участник набрал {points_to_win}, другой на 1 меньше)")
                        elif ((score1 > points_to_win and score2 >= points_to_win) or (score2 > points_to_win and score1 >= points_to_win)) and difference == 1:
                            # Специальное правило: если оба участника набрали больше "очков для победы" и разница = 1, то сет продолжается (например, 12:11 или 11:12)
                            print(f"Счет {score1}:{score2} разрешен - сет продолжается")
                        elif loser_score >= (points_to_win - 1) and not (((score1 > points_to_win and score2 >= points_to_win) or (score2 > points_to_win and score1 >= points_to_win)) and difference == 1) and not ((score1 == points_to_win and score2 == (points_to_win - 1)) or (score2 == points_to_win and score1 == (points_to_win - 1))):
                            # Если у проигравшего очков больше или равно ("очков для победы" - 1), то разница должна быть ровно 2
                            if difference != 2:
                                return jsonify({
                                    'success': False,
                                    'error': f'Неверный счет в сете {set_number}: {score1}:{score2}. Если у проигравшего ({loser_score}) очков больше или равно ({points_to_win - 1}), то разница должна быть ровно 2 очка.'
                                }), 400
                        
                        # Если сет помечен как завершенный, проверяем правила победы
                        if completed:
                            # Проверяем: кто-то набрал необходимое количество очков И разница больше 1
                            # Равный счет (например, 11:11) не считается завершенным
                            # Счет с разницей 1 (например, 11:10, 12:11) не считается завершенным
                            if not ((score1 >= points_to_win or score2 >= points_to_win) and 
                                   difference > 1 and 
                                   not (score1 == points_to_win and score2 == points_to_win) and
                                   not (((score1 > points_to_win and score2 >= points_to_win) or (score2 > points_to_win and score1 >= points_to_win)) and difference == 1) and
                                   not ((score1 == points_to_win and score2 == (points_to_win - 1)) or (score2 == points_to_win and score1 == (points_to_win - 1)))):
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
                old_status = match.status
                if 'sets_won_1' in data and 'sets_won_2' in data:
                    sets_won_1 = data['sets_won_1']
                    sets_won_2 = data['sets_won_2']
                    
                    logger.info(f"[update_match] Анализ выигранных сетов для матча {match_id}: sets_won_1={sets_won_1}, sets_won_2={sets_won_2}, текущий статус={old_status}")
                    
                    # Если счёт 1:1, матч ещё не завершён
                    if sets_won_1 == 1 and sets_won_2 == 1:
                        match.status = 'играют'
                    # Если кто-то выиграл 2 сета, матч завершён
                    elif sets_won_1 >= 2 or sets_won_2 >= 2:
                        match.status = 'завершен'
                        logger.info(f"[update_match] Матч {match_id} завершен по выигранным сетам: {sets_won_1}:{sets_won_2}")
                    # Если счёт 0:0 или 1:0/0:1, матч в процессе
                    else:
                        match.status = 'играют'
                else:
                    # Если нет данных о выигранных сетах, считаем матч завершённым
                    match.status = 'завершен'
                    logger.info(f"[update_match] Матч {match_id} завершен (нет данных о выигранных сетах)")
                
                if old_status != match.status:
                    logger.info(f"[update_match] Статус матча {match_id} изменен: {old_status} -> {match.status}")
                
                # Начисляем очки участникам матча только если матч завершён (кто-то выиграл 2 сета)
                if match.status == 'завершен' and match.winner_id is not None:
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
                    old_status = match.status
                    match.status = data['status']
                    logger.info(f"[update_match] Статус матча {match_id} изменен: {old_status} -> {match.status}")
                
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
            
            # Если матч начался (статус изменился на "в_процессе" или "играют"), устанавливаем реальное время начала
            # Используем локальное время для учета часового пояса пользователя
            if match.status in ['в_процессе', 'играют'] and not match.actual_start_time:
                match.actual_start_time = datetime.now()
                db.session.commit()
                logger.info(f"[РЕАЛЬНОЕ ВРЕМЯ] Начало матча {match_id}: {match.actual_start_time}")
            
            match.updated_at = datetime.now()
            db.session.commit()
            
            # Обновляем объект из базы для получения актуального статуса
            db.session.refresh(match)
            logger.info(f"[update_match] Текущий статус матча {match_id} после сохранения: '{match.status}'")
            
            # Если матч завершен, устанавливаем реальное время окончания и пересчитываем расписание
            # Используем локальное время для учета часового пояса пользователя
            if match.status == 'завершен':
                logger.info(f"[update_match] Матч {match_id} завершен, начинаем пересчет расписания")
                if not match.actual_end_time:
                    match.actual_end_time = datetime.now()
                    db.session.commit()
                    logger.info(f"[update_match] Установлено actual_end_time для матча {match_id}: {match.actual_end_time}")
                
                # Пересчитываем время следующих матчей на той же площадке
                try:
                    logger.info(f"[update_match] Вызов функции пересчета для матча {match_id}")
                    recalculate_schedule_after_match_completion(match_id, Tournament, Match, db)
                    logger.info(f"[update_match] Функция пересчета завершена для матча {match_id}")
                except Exception as e:
                    logger.error(f"[update_match] Ошибка при пересчете расписания после завершения матча {match_id}: {e}", exc_info=True)
            
            # Проверяем завершение турнира после обновления матча
            from routes.main import update_tournament_status
            tournament = Tournament.query.get(match.tournament_id)
            if tournament:
                participants = Participant.query.filter_by(tournament_id=tournament.id).all()
                matches = Match.query.filter_by(tournament_id=tournament.id).all()
                tournament_completed = update_tournament_status(tournament, participants, matches, db)
                if tournament_completed:
                    logger.info(f"Турнир {tournament.id} '{tournament.name}' автоматически завершен после обновления матча {match_id}")
            
            logger.info(f"Матч {match_id} обновлен")
            return jsonify({'success': True, 'message': 'Матч успешно обновлен'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при обновлении матча: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при обновлении матча: {str(e)}'}), 500

    @app.route('/api/refresh-csrf-token', methods=['GET'])
    def refresh_csrf_token():
        """Обновление CSRF токена"""
        from flask import session
        from flask_wtf.csrf import generate_csrf
        
        # Проверяем авторизацию через сессию
        if 'admin_id' not in session:
            return jsonify({'error': 'Необходима авторизация'}), 401
        
        try:
            # Генерируем новый CSRF токен
            new_token = generate_csrf()
            logger.info("CSRF токен обновлен для сессии")
            return jsonify({'success': True, 'csrf_token': new_token})
        except Exception as e:
            logger.error(f"Ошибка при обновлении CSRF токена: {str(e)}")
            return jsonify({'success': False, 'error': 'Ошибка при обновлении токена'}), 500

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
            
        if admin.id != tournament.admin_id and session.get('admin_email') != 'admin@system':
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
            # Создаем умное расписание с сохранением результатов
            matches_created = create_smart_schedule(tournament, participants, Match, db, preserve_results=True)
            
            db.session.commit()
            
            logger.info(f"Пересоздано расписание для турнира {tournament.name}: {matches_created} матчей")
            return jsonify({
                'message': f'Расписание пересоздано с сохранением результатов: {matches_created} матчей',
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
                    from models.match_log import MatchLog
                    MatchLog.query.filter_by(tournament_id=tournament_id).delete()
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
            from models.match_log import MatchLog
            MatchLog.query.delete()
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
    
    @app.route('/api/admin/version', methods=['GET'])
    def admin_get_version():
        """Получение информации о версии приложения"""
        from flask import session
        import subprocess
        import os
        from datetime import datetime
        
        # Проверяем авторизацию системного администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403
        
        try:
            version_info = {
                'git_commit_hash': None,
                'git_commit_message': None,
                'git_commit_date': None,
                'git_branch': None,
                'has_uncommitted_changes': False,
                'last_deploy_time': None,
                'app_file_modified': None
            }
            
            # Получаем директорию приложения
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Находим путь к git
            git_path = None
            possible_paths = ['/usr/bin/git', '/usr/local/bin/git', 'git']
            import shutil
            for path in possible_paths:
                full_path = shutil.which(path) if path == 'git' else (path if os.path.exists(path) else None)
                if full_path:
                    git_path = full_path
                    break
            
            # Проверяем git информацию
            if git_path:
                try:
                    # Текущий коммит
                    result = subprocess.run(
                        [git_path, 'rev-parse', 'HEAD'],
                        cwd=app_dir,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        env={'PATH': os.environ.get('PATH', '/usr/bin:/usr/local/bin:/bin')}
                    )
                    if result.returncode == 0:
                        version_info['git_commit_hash'] = result.stdout.strip()[:7]
                    
                    # Сообщение коммита
                    # Подготавливаем окружение с правильной кодировкой
                    git_env = os.environ.copy()
                    git_env['PATH'] = os.environ.get('PATH', '/usr/bin:/usr/local/bin:/bin')
                    # Для Windows устанавливаем кодировку, для Linux - UTF-8
                    if os.name == 'nt':  # Windows
                        git_env['PYTHONIOENCODING'] = 'utf-8'
                        git_env['PYTHONLEGACYWINDOWSSTDIO'] = '0'  # Отключаем legacy режим
                        # Устанавливаем UTF-8 для консоли Windows
                        git_env['CHCP'] = '65001'  # UTF-8 кодовая страница
                        # Пробуем установить UTF-8 для git на Windows
                        git_env.pop('LANG', None)
                        git_env.pop('LC_ALL', None)
                    else:  # Linux/Unix
                        git_env['LANG'] = 'en_US.UTF-8'
                        git_env['LC_ALL'] = 'en_US.UTF-8'
                    
                    # На Windows используем другой подход для получения сообщения коммита
                    # Пробуем получить напрямую из git объекта, минуя проблему с кодировкой консоли
                    if os.name == 'nt':
                        # Сначала получаем hash коммита
                        commit_hash_result = subprocess.run(
                            [git_path, 'rev-parse', 'HEAD'],
                            cwd=app_dir,
                            capture_output=True,
                            text=False,
                            timeout=5,
                            env=git_env
                        )
                        if commit_hash_result.returncode == 0:
                            commit_hash = commit_hash_result.stdout.strip().decode('utf-8', errors='ignore')
                            # Получаем сообщение коммита напрямую из объекта
                            result = subprocess.run(
                                [git_path, 'cat-file', 'commit', commit_hash],
                                cwd=app_dir,
                                capture_output=True,
                                text=False,
                                timeout=5,
                                env=git_env
                            )
                            if result.returncode == 0:
                                # Парсим сообщение коммита из вывода cat-file
                                # Сообщение находится после первой пустой строки
                                commit_output = result.stdout
                                try:
                                    commit_output_str = commit_output.decode('utf-8', errors='replace')
                                    # Находим первую пустую строку после заголовков
                                    lines = commit_output_str.split('\n')
                                    message_lines = []
                                    empty_line_found = False
                                    for line in lines:
                                        if empty_line_found:
                                            if line.strip():
                                                message_lines.append(line.strip())
                                        elif line.strip() == '':
                                            empty_line_found = True
                                    # Берем только первую строку сообщения (subject)
                                    if message_lines:
                                        result.stdout = message_lines[0].encode('utf-8')
                                    else:
                                        # Если не получилось распарсить, используем старый способ
                                        result.returncode = 1
                                except Exception as e:
                                    logger.warning(f"Ошибка при парсинге сообщения коммита: {e}")
                                    result.returncode = 1
                        
                        # Если предыдущий способ не сработал, пробуем через log с UTF-8
                        if result.returncode != 0:
                            result = subprocess.run(
                                f'chcp 65001 >nul && "{git_path}" log -1 --pretty=format:"%s"',
                                cwd=app_dir,
                                capture_output=True,
                                shell=True,
                                text=False,
                                timeout=5,
                                env=git_env
                            )
                    else:
                        result = subprocess.run(
                            [git_path, 'log', '-1', '--pretty=format:%s'],
                            cwd=app_dir,
                            capture_output=True,
                            text=False,  # Получаем bytes для корректной обработки кодировки
                            timeout=5,
                            env=git_env
                        )
                    if result.returncode == 0:
                        try:
                            # Пробуем разные кодировки для Windows и Linux
                            commit_message_bytes = result.stdout
                            if isinstance(commit_message_bytes, bytes):
                                # Убираем BOM и пробельные символы только после декодирования
                                # Удаляем BOM если есть (может быть в начале)
                                if commit_message_bytes.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                                    commit_message_bytes = commit_message_bytes[3:]
                                elif commit_message_bytes.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                                    commit_message_bytes = commit_message_bytes[2:]
                                elif commit_message_bytes.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                                    commit_message_bytes = commit_message_bytes[2:]
                                
                                # Определяем приоритет кодировок в зависимости от ОС
                                encodings_to_try = []
                                if os.name == 'nt':  # Windows
                                    # На Windows git может использовать разные кодировки
                                    # Пробуем UTF-8 сначала, так как современный git на Windows обычно использует UTF-8
                                    encodings_to_try = ['utf-8', 'cp1251', 'cp866', 'latin1']
                                else:  # Linux/Unix
                                    # На Linux обычно UTF-8
                                    encodings_to_try = ['utf-8', 'latin1']
                                
                                commit_message_decoded = None
                                for encoding in encodings_to_try:
                                    try:
                                        commit_message_decoded = commit_message_bytes.decode(encoding)
                                        # Проверяем, что декодирование дало осмысленный результат
                                        # Убираем пробельные символы только после успешного декодирования
                                        commit_message_decoded = commit_message_decoded.strip()
                                        if commit_message_decoded:
                                            break
                                    except (UnicodeDecodeError, LookupError):
                                        continue
                                
                                if commit_message_decoded:
                                    commit_message = commit_message_decoded
                                else:
                                    # В крайнем случае используем replace для замены нечитаемых символов
                                    commit_message = commit_message_bytes.decode('utf-8', errors='replace').strip()
                            else:
                                # Если уже строка, просто убираем пробельные символы
                                commit_message = commit_message_bytes.strip() if isinstance(commit_message_bytes, str) else str(commit_message_bytes).strip()
                            
                            # Исправление: восстанавливаем пропущенные первые буквы в известных словах
                            # Это исправляет проблему с кодировкой при создании коммита на Windows
                            if commit_message:
                                corrections = {
                                    'обавлена': 'Добавлена',
                                    'бнулить': 'обнулить',
                                    'исправлена': 'Исправлена'
                                }
                                
                                # Проверяем начало сообщения и исправляем известные ошибки
                                words = commit_message.split()
                                if words:
                                    # Исправляем первое слово если оно есть в словаре исправлений
                                    if words[0] in corrections:
                                        words[0] = corrections[words[0]]
                                    # Также проверяем другие слова на известные ошибки
                                    for i, word in enumerate(words):
                                        # Убираем кавычки и другие символы для проверки
                                        clean_word = word.strip("'\".,!?;:")
                                        if clean_word in corrections:
                                            words[i] = word.replace(clean_word, corrections[clean_word])
                                    commit_message = ' '.join(words)
                            
                            version_info['git_commit_message'] = commit_message
                        except Exception as e:
                            logger.warning(f"Не удалось декодировать сообщение коммита: {e}")
                            logger.warning(f"Байты сообщения: {result.stdout[:100] if result.stdout else 'None'}")
                            version_info['git_commit_message'] = None
                    
                    # Дата коммита
                    result = subprocess.run(
                        [git_path, 'log', '-1', '--pretty=format:%ai'],
                        cwd=app_dir,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        env={'PATH': os.environ.get('PATH', '/usr/bin:/usr/local/bin:/bin')}
                    )
                    if result.returncode == 0:
                        version_info['git_commit_date'] = result.stdout.strip()
                    
                    # Ветка
                    result = subprocess.run(
                        [git_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
                        cwd=app_dir,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        env={'PATH': os.environ.get('PATH', '/usr/bin:/usr/local/bin:/bin')}
                    )
                    if result.returncode == 0:
                        version_info['git_branch'] = result.stdout.strip()
                    
                    # Проверка несохраненных изменений
                    result = subprocess.run(
                        [git_path, 'diff', '--quiet'],
                        cwd=app_dir,
                        timeout=5,
                        env={'PATH': os.environ.get('PATH', '/usr/bin:/usr/local/bin:/bin')}
                    )
                    version_info['has_uncommitted_changes'] = (result.returncode != 0)
                
                except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                    logger.warning(f"Не удалось получить git информацию: {e}")
            else:
                logger.warning("Git не найден в системе. Информация о версии будет ограничена.")
                # Попробуем получить информацию из файла .git/HEAD
                try:
                    git_head_path = os.path.join(app_dir, '.git', 'HEAD')
                    if os.path.exists(git_head_path):
                        with open(git_head_path, 'r') as f:
                            head_content = f.read().strip()
                            if head_content.startswith('ref: '):
                                version_info['git_branch'] = head_content.replace('ref: refs/heads/', '')
                            else:
                                version_info['git_commit_hash'] = head_content[:7] if len(head_content) >= 7 else head_content
                except Exception as e:
                    logger.warning(f"Не удалось прочитать .git/HEAD: {e}")
            
            # Дата последнего изменения app.py
            try:
                app_file_path = os.path.join(app_dir, 'app.py')
                if os.path.exists(app_file_path):
                    mtime = os.path.getmtime(app_file_path)
                    version_info['app_file_modified'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.warning(f"Не удалось получить дату изменения app.py: {e}")
            
            return jsonify({'success': True, 'version': version_info})
        except Exception as e:
            logger.error(f"Ошибка при получении версии: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении версии'}), 500
    
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
                
                # Удаляем записи журнала матчей
                from models.match_log import MatchLog
                match_logs_deleted = MatchLog.query.filter_by(tournament_id=tournament.id).delete()
                logger.info(f"Удалено записей журнала: {match_logs_deleted}")
                
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
        """API для подачи заявки на участие в турнире (лист ожидания)"""
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
            skill_level = data.get('skill_level', '').strip()
            enable_telegram = data.get('enable_telegram', False)
            
            if not tournament_id or not skill_level:
                return jsonify({'success': False, 'error': 'Необходимо указать ID турнира и уровень навыков'}), 400
            # Имя обязательно только если не выбран Telegram-способ
            if not enable_telegram and not participant_name:
                return jsonify({'success': False, 'error': 'Необходимо указать имя участника или выбрать подачу через Telegram'}), 400
            
            # Проверяем существование турнира
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Проверяем, что турнир принимает заявки
            allowed_registration_statuses = ['регистрация', 'Регистрация участников']
            if tournament.status not in allowed_registration_statuses:
                return jsonify({'success': False, 'error': 'Турнир не принимает заявки на участие'}), 400
            
            # Проверяем, не участвует ли уже участник в турнире
            existing_participant = Participant.query.filter_by(
                tournament_id=tournament_id, 
                name=participant_name
            ).first()
            
            if existing_participant:
                return jsonify({'success': False, 'error': 'Вы уже участвуете в этом турнире'}), 400
            
            # Проверяем, не подал ли уже участник заявку в лист ожидания
            # Безопасная проверка на случай отсутствия колонки status
            try:
                existing_waiting = WaitingList.query.filter_by(
                    tournament_id=tournament_id, 
                    name=participant_name,
                    status='ожидает'
                ).first()
            except Exception as status_e:
                logger.warning(f"Ошибка при проверке статуса заявки (возможно колонка status отсутствует): {status_e}")
                # Если колонка status отсутствует, проверяем без фильтра по статусу
                try:
                    existing_waiting = WaitingList.query.filter_by(
                        tournament_id=tournament_id, 
                        name=participant_name
                    ).first()
                except Exception as e2:
                    logger.error(f"Критическая ошибка при проверке существующей заявки: {e2}")
                    existing_waiting = None
            
            if existing_waiting:
                return jsonify({'success': False, 'error': 'Вы уже подали заявку на участие в этом турнире'}), 400
            
            # Генерируем уникальный токен для привязки к Telegram (только если пользователь выбрал Telegram)
            telegram_token = generate_telegram_token() if enable_telegram else None
            
            # Создаем заявку в лист ожидания
            new_waiting_list_entry = WaitingList(
                tournament_id=tournament_id,
                name=participant_name if participant_name else 'Игрок (Telegram)',
                skill_level=skill_level,
                telegram=None,  # Будет заполнен после сканирования QR-кода
                telegram_token=telegram_token,
                status='ожидает'
            )
            
            try:
                db.session.add(new_waiting_list_entry)
                db.session.commit()
                logger.info(f"Заявка добавлена в лист ожидания: турнир={tournament_id}, имя={participant_name}")
            except Exception as db_e:
                db.session.rollback()
                logger.error(f"Ошибка при добавлении заявки в БД: {db_e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return jsonify({'success': False, 'error': f'Ошибка базы данных: {str(db_e)}'}), 500
            
            # Генерируем QR-код для подключения к боту (только если пользователь выбрал Telegram)
            qr_code = None
            if enable_telegram:
                try:
                    import os
                    bot_username = get_bot_username()
                    logger.info(f"Генерация QR-кода: используется bot_username={bot_username}, APP_ENV={os.environ.get('APP_ENV', 'не установлен')}")
                    qr_code = generate_qr_code(telegram_token, bot_username)
                    logger.info(f"QR-код сгенерирован для участника {participant_name} (токен: {telegram_token[:8]}...)")
                except Exception as e:
                    logger.error(f"Ошибка при генерации QR-кода: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    qr_code = None
            
            telegram_status = " с подключением к Telegram боту" if enable_telegram else ""
            logger.info(f"Участник {participant_name} (уровень: {skill_level}) подал заявку в лист ожидания турнира {tournament.name} (ID: {tournament_id}){telegram_status}")

            # Уведомление администратору турнира в TG, если он ранее указывал Telegram при получении пароля
            try:
                import hashlib
                from utils.telegram_utils import send_telegram_message
                # Ищем токен администратора по соответствию admin_id = hash(email) % 1_000_000
                admin_telegram = None
                from models.token import Token
                tokens = Token.query.all()
                for t in tokens:
                    try:
                        if int(hashlib.md5(t.email.encode('utf-8')).hexdigest(), 16) % 1000000 == tournament.admin_id:
                            if t.telegram:
                                admin_telegram = t.telegram
                                break
                    except Exception:
                        continue
                if admin_telegram:
                    msg = (
                        f"📥 Новая заявка в лист ожидания\n"
                        f"Турнир: {tournament.name} (ID: {tournament.id})\n"
                        f"Игрок: {participant_name if participant_name else 'Игрок (Telegram)'}\n"
                        f"Уровень: {skill_level}"
                    )
                    send_telegram_message(msg, telegram_contact=admin_telegram)
            except Exception as notify_e:
                logger.warning(f"Не удалось отправить уведомление админу турнира в TG: {notify_e}")
            
            return jsonify({
                'success': True, 
                'message': 'Заявка успешно подана в лист ожидания',
                'qr_code': qr_code,
                'telegram_token': telegram_token
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при подаче заявки на участие: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Всегда возвращаем JSON, даже при ошибках
            try:
                return jsonify({'success': False, 'error': f'Ошибка при подаче заявки: {str(e)}'}), 500
            except Exception as json_e:
                logger.error(f"Критическая ошибка при формировании JSON ответа: {json_e}")
                # Fallback: возвращаем простой JSON ответ
                from flask import Response
                return Response('{"success": false, "error": "Критическая ошибка сервера"}', 
                              mimetype='application/json', status=500)

    @app.route('/api/telegram/link-token', methods=['POST'])
    @csrf.exempt  # Исключаем из CSRF защиты, так как запросы приходят от Telegram бота
    def link_telegram_token():
        """API для связывания Telegram Chat ID с токеном заявки"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'success': False, 'error': 'Нет данных'}), 400
            
            token = data.get('token', '').strip()
            chat_id = data.get('chat_id', '').strip()
            
            if not token or not chat_id:
                return jsonify({'success': False, 'error': 'Необходимо указать токен и Chat ID'}), 400
            
            # Ищем заявку с таким токеном (подача заявки)
            waiting_entry = WaitingList.query.filter_by(telegram_token=token).first()
            if waiting_entry:
                # Проверяем, не привязан ли уже токен к другому Chat ID
                if waiting_entry.telegram and waiting_entry.telegram != chat_id:
                    logger.warning(f"Токен {token[:8]}... уже привязан к Chat ID {waiting_entry.telegram}")
                    return jsonify({'success': False, 'error': 'Токен уже привязан к другому аккаунту'}), 400
                waiting_entry.telegram = chat_id
                db.session.commit()
                logger.info(f"✅ Chat ID {chat_id} успешно привязан к заявке участника {waiting_entry.name} (токен: {token[:8]}...)")
                return jsonify({'success': True, 'message': 'Telegram успешно подключен', 'participant_name': waiting_entry.name, 'tournament_id': waiting_entry.tournament_id})

            # Если это не токен заявки, проверяем токен привязки админа (страница 2)
            admin_token_row = Token.query.filter_by(telegram_link_token=token).first()
            if admin_token_row:
                admin_token_row.telegram_chat_id = str(chat_id)
                # Сохраняем и как универсальное поле для совместимости с уведомлениями
                admin_token_row.telegram = str(chat_id)
                # Одноразовый токен можно обнулить, чтобы не использовать повторно
                admin_token_row.telegram_link_token = None
                db.session.commit()
                logger.info(f"✅ Chat ID {chat_id} привязан к администратору (email={admin_token_row.email}) через deep link")
                return jsonify({'success': True, 'message': 'Telegram администратора подключён'})

            logger.warning(f"Попытка привязать несуществующий токен: {token[:8]}...")
            return jsonify({'success': False, 'error': 'Токен не найден или уже использован'}), 404
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при связывании Telegram токена: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при подключении Telegram'}), 500

    @app.route('/api/admin/telegram/generate-link', methods=['POST'])
    def generate_admin_telegram_link():
        """Сгенерировать deep link токен для админа, чтобы привязать chat_id без ручного ввода.
        Вход: email (обяз.), name (опц.)
        Выход: deep_link, link_token
        """
        try:
            data = request.get_json(silent=True) or request.form
            email = (data.get('email') or '').strip()
            name = (data.get('name') or '').strip() or 'Администратор'
            if not email:
                return jsonify({'success': False, 'error': 'Email обязателен'}), 400

            # Берём последнюю запись Token по email или создаём новую черновую
            token_row = Token.query.filter_by(email=email).order_by(Token.created_at.desc()).first()
            if not token_row:
                token_row = Token(email=email, token=0, name=name, created_at=datetime.utcnow(), is_used=False, email_sent=False)
                db.session.add(token_row)
                db.session.commit()

            import secrets
            link_token = secrets.token_urlsafe(32)
            token_row.telegram_link_token = link_token
            db.session.commit()

            from config import Config
            bot_username = Config.TELEGRAM_BOT_USERNAME or 'Q_uickScore_bot'
            deep_link = f"https://t.me/{bot_username}?start={link_token}"
            return jsonify({'success': True, 'deep_link': deep_link, 'link_token': link_token}), 200
        except Exception as e:
            logger.exception('Ошибка генерации admin telegram link')
            return jsonify({'success': False, 'error': 'Не удалось сгенерировать ссылку'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/waiting-list', methods=['GET'])
    def get_waiting_list(tournament_id):
        """API для получения листа ожидания турнира"""
        try:
            from flask import session
            
            # Проверяем права доступа через сессию
            session_admin_id = session.get('admin_id')
            if not session_admin_id:
                return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
            
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Проверяем права доступа к турниру
            if tournament.admin_id != session_admin_id:
                return jsonify({'success': False, 'error': 'Недостаточно прав для доступа к этому турниру'}), 403
            
            # Получаем лист ожидания
            waiting_list = WaitingList.query.filter_by(
                tournament_id=tournament_id,
                status='ожидает'
            ).order_by(WaitingList.created_at.asc()).all()
            
            # Формируем ответ
            waiting_list_data = []
            for entry in waiting_list:
                created_at_str = 'Не указано'
                if entry.created_at:
                    created_at_str = entry.created_at.strftime('%d.%m.%Y %H:%M')
                
                waiting_list_data.append({
                    'id': entry.id,
                    'name': entry.name,
                    'skill_level': entry.skill_level,
                    'created_at': created_at_str,
                    'telegram': entry.telegram if entry.telegram else None
                })
            
            return jsonify({'success': True, 'waiting_list': waiting_list_data})
            
        except Exception as e:
            logger.error(f"Ошибка при получении листа ожидания: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении листа ожидания'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/waiting-list/<int:waiting_id>', methods=['DELETE'])
    def delete_waiting_entry(tournament_id, waiting_id):
        """API: удалить запись из листа ожидания (или пометить как отклонена)."""
        try:
            from flask import session
            session_admin_id = session.get('admin_id')
            if not session_admin_id:
                return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401

            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404

            if tournament.admin_id != session_admin_id:
                return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

            waiting_entry = WaitingList.query.get(waiting_id)
            if not waiting_entry or waiting_entry.tournament_id != tournament_id:
                return jsonify({'success': False, 'error': 'Заявка не найдена'}), 404

            # Получаем сообщение из тела запроса (если есть)
            message_sent = False
            message = None
            try:
                data = request.get_json()
                message = data.get('message') if data else None
            except:
                pass

            # Если есть Telegram и сообщение - отправляем уведомление
            if waiting_entry.telegram and message:
                try:
                    telegram_message = f"📋 <b>Уведомление от администратора турнира</b>\n\n{message}"
                    send_ok = send_telegram_message(telegram_message, telegram_contact=waiting_entry.telegram)
                    if send_ok:
                        message_sent = True
                        logger.info(f"Сообщение об отклонении отправлено участнику {waiting_entry.name} (telegram: {waiting_entry.telegram})")
                    else:
                        logger.warning(f"Не удалось отправить сообщение об отклонении участнику {waiting_entry.name} (telegram: {waiting_entry.telegram})")
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения об отклонении: {e}")

            # Мягкое удаление: помечаем как отклонен, чтобы сохранялась история
            waiting_entry.status = 'отклонен'
            db.session.commit()

            logger.info(f"Заявка из листа ожидания удалена (отклонена): id={waiting_id}, турнир={tournament_id}, имя={waiting_entry.name}")
            return jsonify({
                'success': True, 
                'message': 'Заявка удалена из листа ожидания',
                'message_sent': message_sent
            })
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении из листа ожидания: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении заявки'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/accept-waiting', methods=['POST'])
    def accept_waiting_list(tournament_id):
        """API для принятия заявок из листа ожидания"""
        try:
            from flask import session
            
            # Проверяем права доступа через сессию
            session_admin_id = session.get('admin_id')
            if not session_admin_id:
                return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
            
            data = request.get_json()
            waiting_ids = data.get('waiting_ids', [])
            
            if not waiting_ids:
                return jsonify({'success': False, 'error': 'Не выбраны заявки для принятия'}), 400
            
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Проверяем права доступа к турниру
            if tournament.admin_id != session_admin_id:
                return jsonify({'success': False, 'error': 'Недостаточно прав для доступа к этому турниру'}), 403
            
            accepted_count = 0
            for waiting_id in waiting_ids:
                # Получаем заявку из листа ожидания
                waiting_entry = WaitingList.query.get(waiting_id)
                if not waiting_entry or waiting_entry.tournament_id != tournament_id:
                    continue
                
                # Проверяем, не участвует ли уже участник в турнире
                existing_participant = Participant.query.filter_by(
                    tournament_id=tournament_id,
                    name=waiting_entry.name
                ).first()
                
                if existing_participant:
                    # Помечаем заявку как отклоненную
                    waiting_entry.status = 'отклонен'
                    continue
                
                # Добавляем участника в турнир
                new_participant = Participant(
                    tournament_id=tournament_id,
                    name=waiting_entry.name,
                    telegram=waiting_entry.telegram,  # Переносим Telegram контакт
                    points=0,
                    registered_at=tournament.created_at  # Устанавливаем время регистрации как время создания турнира
                )
                
                db.session.add(new_participant)
                
                # Автоматически добавляем игрока в список игроков
                player_name = waiting_entry.name.strip()
                existing_player = Player.query.filter_by(name=player_name).first()
                if not existing_player:
                    new_player = Player(name=player_name)
                    db.session.add(new_player)
                    logger.info(f"Игрок '{player_name}' добавлен в список игроков из листа ожидания")
                else:
                    # Обновляем время последнего использования
                    existing_player.last_used_at = datetime.utcnow()
                    logger.info(f"Время последнего использования игрока '{player_name}' обновлено из листа ожидания")
                
                # Помечаем заявку как принятую
                waiting_entry.status = 'принят'
                accepted_count += 1
                
                # Отправляем уведомление в Telegram, если указан контакт
                if waiting_entry.telegram:
                    try:
                        # Формируем сообщение для участника
                        notification_message = f"""
🎉 <b>Поздравляем, {waiting_entry.name}!</b>

Ваша заявка на участие в турнире <b>"{tournament.name}"</b> одобрена!

📋 <b>Информация о турнире:</b>
🏆 Турнир: {tournament.name}
⚽ Вид спорта: {tournament.sport_type}
📅 Начало: {tournament.start_date.strftime('%d.%m.%Y') if tournament.start_date else 'Не указано'}
⏰ Время матчей: {tournament.start_time.strftime('%H:%M') if tournament.start_time else 'Не указано'}

Ожидайте расписание матчей. Удачи! 💪
"""
                        
                        logger.info(f"Попытка отправки уведомления участнику {waiting_entry.name} (Telegram: {waiting_entry.telegram})")
                        success = send_telegram_message(notification_message, telegram_contact=waiting_entry.telegram)
                        
                        if success:
                            logger.info(f"✅ Уведомление успешно отправлено участнику {waiting_entry.name}")
                        else:
                            logger.warning(f"⚠️ Не удалось отправить уведомление участнику {waiting_entry.name}. Проверьте настройки Telegram")
                    except Exception as e:
                        logger.error(f"❌ Ошибка при отправке уведомления участнику {waiting_entry.name}: {e}")
                else:
                    logger.info(f"ℹ️  Telegram не указан для участника {waiting_entry.name}, уведомление не отправлено")
            
            db.session.commit()
            
            # Автоматически пересоставляем расписание для новых участников
            if accepted_count > 0:
                # Используем create_smart_schedule для полного пересчета расписания
                # с сохранением результатов существующих матчей
                try:
                    # Получаем всех участников турнира
                    all_participants = Participant.query.filter_by(tournament_id=tournament_id).all()
                    logger.info(f"Пересоставление расписания: добавлено {accepted_count} участников, всего участников: {len(all_participants)}")
                    
                    # Вызываем create_smart_schedule с правильными параметрами
                    matches_created = create_smart_schedule(tournament, all_participants, Match, db, preserve_results=True)
                    db.session.commit()
                    
                    logger.info(f"Расписание автоматически пересоставлено: создано/обновлено {matches_created} матчей для {accepted_count} новых участников из листа ожидания")
                except Exception as e:
                    logger.error(f"Ошибка при автоматическом пересоставлении расписания: {e}")
                    # Если не удалось пересчитать расписание, создаем матчи вручную
                    all_participants = Participant.query.filter_by(tournament_id=tournament_id).all()
                    
                    for waiting_id in waiting_ids:
                        waiting_entry = WaitingList.query.get(waiting_id)
                        if not waiting_entry or waiting_entry.tournament_id != tournament_id or waiting_entry.status != 'принят':
                            continue
                        
                        new_participant = Participant.query.filter_by(
                            tournament_id=tournament_id,
                            name=waiting_entry.name
                        ).first()
                        
                        if not new_participant:
                            continue
                        
                        for existing_participant in all_participants:
                            if existing_participant.id != new_participant.id:
                                existing_match = Match.query.filter_by(
                                    tournament_id=tournament_id,
                                    participant1_id=min(new_participant.id, existing_participant.id),
                                    participant2_id=max(new_participant.id, existing_participant.id)
                                ).first()
                                
                                if not existing_match:
                                    new_match = Match(
                                        tournament_id=tournament_id,
                                        participant1_id=min(new_participant.id, existing_participant.id),
                                        participant2_id=max(new_participant.id, existing_participant.id),
                                        court_number=1,
                                        status='запланирован'
                                    )
                                    db.session.add(new_match)
                    
                    db.session.commit()
                    logger.info(f"Созданы матчи для {accepted_count} новых участников из листа ожидания (fallback)")
            
            logger.info(f"Принято {accepted_count} заявок из листа ожидания турнира {tournament.name}")
            
            return jsonify({
                'success': True, 
                'message': f'Принято {accepted_count} заявок из листа ожидания. Расписание автоматически пересоставлено.',
                'accepted_count': accepted_count
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при принятии заявок из листа ожидания: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при принятии заявок'}), 500
    @app.route('/api/tournaments/<int:tournament_id>/generate-schedule', methods=['POST'])
    def generate_schedule(tournament_id):
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
            
            # Создаем новое расписание с сохранением результатов
            matches_created = create_smart_schedule(tournament, participants, Match, db, preserve_results=True)
            
            if matches_created > 0:
                # Изменяем статус турнира на "Регистрация участников"
                tournament.status = 'Регистрация участников'
                db.session.commit()
                logger.info(f"Расписание составлено для турнира {tournament.name}: создано {matches_created} матчей, статус изменен на 'Регистрация участников'")
                return jsonify({
                    'success': True, 
                    'message': f'Расписание успешно составлено! Создано {matches_created} матчей. Статус турнира изменен на "Регистрация участников".'
                })
            else:
                return jsonify({'success': False, 'error': 'Не удалось создать расписание'}), 500
                
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при составлении расписания: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при составлении расписания'}), 500


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
            
            # Автоматически добавляем игрока в список игроков
            player_name = name.strip()
            existing_player = Player.query.filter_by(name=player_name).first()
            if not existing_player:
                new_player = Player(name=player_name)
                db.session.add(new_player)
                logger.info(f"Игрок '{player_name}' добавлен в список игроков (опоздавший участник)")
            else:
                # Обновляем время последнего использования
                existing_player.last_used_at = datetime.utcnow()
                logger.info(f"Время последнего использования игрока '{player_name}' обновлено (опоздавший участник)")
            
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

    @app.route('/api/debug/test-email', methods=['GET', 'POST'])
    @csrf.exempt
    def debug_test_email():
        """Тестирование отправки email для отладки"""
        try:
            if request.method == 'GET':
                test_email = request.args.get('email', 'test@example.com')
            else:
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

    @app.route('/api/debug/email-config', methods=['GET'])
    def debug_email_config():
        """Диагностика настроек email для Railway"""
        import os
        from flask import current_app
        
        # Получаем настройки из переменных окружения
        env_config = {
            'MAIL_SERVER': os.environ.get('MAIL_SERVER'),
            'MAIL_PORT': os.environ.get('MAIL_PORT'),
            'MAIL_USERNAME': os.environ.get('MAIL_USERNAME'),
            'MAIL_PASSWORD': '***' if os.environ.get('MAIL_PASSWORD') else None,
            'MAIL_DEFAULT_SENDER': os.environ.get('MAIL_DEFAULT_SENDER'),
            'FLASK_ENV': os.environ.get('FLASK_ENV'),
            'RAILWAY_ENVIRONMENT': os.environ.get('RAILWAY_ENVIRONMENT'),
        }
        
        # Получаем настройки из конфигурации Flask
        flask_config = {
            'MAIL_SERVER': current_app.config.get('MAIL_SERVER'),
            'MAIL_PORT': current_app.config.get('MAIL_PORT'),
            'MAIL_USERNAME': current_app.config.get('MAIL_USERNAME'),
            'MAIL_PASSWORD': '***' if current_app.config.get('MAIL_PASSWORD') else None,
            'MAIL_DEFAULT_SENDER': current_app.config.get('MAIL_DEFAULT_SENDER'),
        }
        
        return jsonify({
            'success': True,
            'environment_variables': env_config,
            'flask_config': flask_config,
            'message': 'Проверьте переменные окружения на Railway'
        })

    @app.route('/api/admin/tokens', methods=['GET'])
    def admin_get_tokens():
        """Получение списка токенов для админ-панели"""
        try:
            # Получаем параметр max из запроса
            max_tokens = request.args.get('max', type=int, default=10)
            
            # Получаем токены с ограничением по количеству
            tokens = Token.query.order_by(Token.created_at.desc()).limit(max_tokens).all()
            
            token_list = []
            for token in tokens:
                token_data = {
                    'id': token.id,
                    'email': token.email,
                    'token': token.token,
                    'name': token.name,
                    'created_at': token.created_at.strftime('%d.%m.%Y %H:%M'),
                    'is_used': token.is_used,
                    'used_at': token.used_at.strftime('%d.%m.%Y %H:%M') if token.used_at else None,
                    'email_sent': token.email_sent,
                    'email_sent_at': token.email_sent_at.strftime('%d.%m.%Y %H:%M') if token.email_sent_at else None,
                    'email_status': token.email_status
                }
                token_list.append(token_data)
            
            # Получаем общую статистику по всем токенам в базе
            all_tokens = Token.query.all()
            total_tokens = len(all_tokens)
            pending_count = len([t for t in all_tokens if t.email_status == 'pending'])
            manual_count = len([t for t in all_tokens if t.email_status == 'manual'])
            sent_count = len([t for t in all_tokens if t.email_status == 'sent'])
            failed_count = len([t for t in all_tokens if t.email_status == 'failed'])
            
            return jsonify({
                'success': True,
                'tokens': token_list,
                'total': total_tokens,
                'pending': pending_count,
                'manual': manual_count,
                'sent': sent_count,
                'failed': failed_count,
                'showing': len(token_list),  # Количество отображаемых токенов
                'max_tokens': int(Settings.get_setting('max_tokens', '10'))  # Текущее максимальное количество паролей
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении токенов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении токенов'}), 500

    @app.route('/api/admin/send-token-manually', methods=['POST'])
    @csrf.exempt  # Исключаем из CSRF защиты для API
    def admin_send_token_manually():
        """Ручная отправка токена администратором"""
        try:
            data = request.get_json()
            logger.info(f"Ручная отправка токена: {data}")
            
            token_id = data.get('token_id')
            custom_email = data.get('email')  # Опционально - другой email для отправки
            
            if not token_id:
                return jsonify({'success': False, 'error': 'Не указан ID токена'}), 400
            
            # Находим токен
            token = Token.query.get(token_id)
            if not token:
                return jsonify({'success': False, 'error': 'Токен не найден'}), 404
            
            # Определяем email для отправки
            target_email = custom_email or token.email
            
            # Импортируем функцию отправки email
            from routes.main import send_token_email
            
            logger.info(f"Ручная отправка токена {token.token} на {target_email}")
            
            # Пытаемся отправить email
            result = send_token_email(target_email, token.name, token.token)
            
            if result:
                # Обновляем статус токена
                token.email_sent = True
                token.email_sent_at = datetime.utcnow()
                token.email_status = 'sent'
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': f'Токен {token.token} успешно отправлен на {target_email}'
                })
            else:
                # Обновляем статус как требующий ручной отправки
                token.email_status = 'manual'
                db.session.commit()
                
                return jsonify({
                    'success': False,
                    'message': f'Не удалось отправить токен {token.token} на {target_email}. Требуется ручная отправка.'
                })
                
        except Exception as e:
            logger.error(f"Ошибка при ручной отправке токена: {e}")
            logger.error(f"Тип ошибки: {type(e).__name__}")
            logger.error(f"Детали ошибки: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при отправке: {str(e)}'}), 500

    @app.route('/api/admin/send-email-external', methods=['POST'])
    @csrf.exempt  # Исключаем из CSRF защиты для API
    def send_email_external():
        """Отправка email через внешний сервис (для Railway)"""
        try:
            import os
            import requests
            from datetime import datetime
            
            data = request.get_json()
            email = data.get('email')
            name = data.get('name')
            token = data.get('token')
            
            if not all([email, name, token]):
                return jsonify({'success': False, 'error': 'Не указаны все необходимые параметры'}), 400
            
            # Попробуем использовать EmailJS
            emailjs_url = "https://api.emailjs.com/api/v1.0/email/send"
            emailjs_service_id = os.environ.get('EMAILJS_SERVICE_ID')
            emailjs_template_id = os.environ.get('EMAILJS_TEMPLATE_ID')
            emailjs_user_id = os.environ.get('EMAILJS_USER_ID')
            
            logger.info(f"Проверка настроек EmailJS:")
            logger.info(f"EMAILJS_SERVICE_ID: {emailjs_service_id}")
            logger.info(f"EMAILJS_TEMPLATE_ID: {emailjs_template_id}")
            logger.info(f"EMAILJS_USER_ID: {emailjs_user_id}")
            
            if emailjs_service_id and emailjs_template_id and emailjs_user_id:
                logger.info(f"Попытка отправки через EmailJS на {email}")
                
                payload = {
                    'service_id': emailjs_service_id,
                    'template_id': emailjs_template_id,
                    'user_id': emailjs_user_id,
                    'template_params': {
                        'to_email': email,
                        'to_name': name,
                        'token': token,
                        'from_name': 'Турнирный Ассистент'
                    }
                }
                
                logger.info(f"Отправка запроса на EmailJS: {emailjs_url}")
                logger.info(f"Payload: {payload}")
                
                # Добавляем заголовки для имитации браузера
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Origin': 'https://dashboard.emailjs.com',
                    'Referer': 'https://dashboard.emailjs.com/'
                }
                
                response = requests.post(emailjs_url, json=payload, headers=headers, timeout=10)
                logger.info(f"Ответ EmailJS: статус {response.status_code}, текст: {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"[SUCCESS] Email отправлен через EmailJS на {email}")
                    return jsonify({
                        'success': True,
                        'message': f'Email успешно отправлен на {email} через внешний сервис'
                    })
                else:
                    logger.error(f"[ERROR] EmailJS вернул статус {response.status_code}")
                    return jsonify({
                        'success': False,
                        'error': f'Внешний сервис вернул ошибку: {response.status_code} - {response.text}'
                    })
            else:
                logger.warning("EmailJS не настроен - отсутствуют переменные окружения")
                
                # Попробуем использовать простой webhook
                webhook_url = os.environ.get('EMAIL_WEBHOOK_URL')
                if webhook_url:
                    logger.info(f"Попытка отправки через webhook: {webhook_url}")
                    
                    payload = {
                        'to': email,
                        'subject': 'Ваш токен для создания турниров',
                        'body': f"""
Здравствуйте, {name}!

Ваш токен для создания турниров: {token}

Этот токен действителен в течение 30 дней.
Используйте его для входа в систему как администратор турнира.

С уважением,
Команда турнирной системы
                        """,
                        'from': 'tournaments.master@gmail.com'
                    }
                    
                    try:
                        response = requests.post(webhook_url, json=payload, timeout=10)
                        if response.status_code == 200:
                            logger.info(f"[SUCCESS] Email отправлен через webhook на {email}")
                            return jsonify({
                                'success': True,
                                'message': f'Email успешно отправлен на {email} через webhook'
                            })
                        else:
                            logger.error(f"[ERROR] Webhook вернул статус {response.status_code}")
                    except Exception as webhook_error:
                        logger.error(f"[ERROR] Ошибка webhook: {webhook_error}")
                
                # Если ничего не работает, сохраняем для ручной отправки
                logger.info("Все внешние сервисы недоступны. Сохраняем для ручной отправки.")
                
                # Сохраняем в файл для ручной отправки
                try:
                    with open('tokens.txt', 'a', encoding='utf-8') as f:
                        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {email} - {name} - Токен: {token} (RAILWAY EXTERNAL API - ТРЕБУЕТСЯ РУЧНАЯ ОТПРАВКА)\n")
                except Exception as file_error:
                    logger.warning(f"Не удалось сохранить в файл: {file_error}")
                
                return jsonify({
                    'success': False,
                    'error': 'Внешний email сервис не настроен. Токен сохранен для ручной отправки. Добавьте переменные EMAILJS_* или EMAIL_WEBHOOK_URL на Railway'
                })
                
        except Exception as e:
            logger.error(f"Ошибка при отправке через внешний сервис: {e}")
            return jsonify({'success': False, 'error': f'Ошибка при отправке: {str(e)}'}), 500

    @app.route('/api/admin/update-max-tokens', methods=['POST'])
    def update_max_tokens():
        """Обновление максимального количества токенов"""
        try:
            data = request.get_json()
            max_tokens = data.get('max_tokens')
            
            if not max_tokens or not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 100:
                return jsonify({
                    'success': False,
                    'error': 'Некорректное значение максимального количества токенов (должно быть от 1 до 100)'
                }), 400
            
            # Обновляем настройку
            Settings.set_setting('max_tokens', str(max_tokens), 'Максимальное количество токенов для создания турниров')
            
            logger.info(f"Максимальное количество токенов обновлено на {max_tokens}")
            
            return jsonify({
                'success': True,
                'message': f'Максимальное количество токенов обновлено на {max_tokens}',
                'max_tokens': max_tokens
            })
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении максимального количества токенов: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при обновлении настроек'}), 500

    # Маршруты для работы со списком игроков
    @app.route('/api/players', methods=['GET'])
    def get_players():
        """Получение списка всех игроков"""
        try:
            players = Player.query.order_by(Player.name).all()
            players_data = []
            for player in players:
                players_data.append({
                    'id': player.id,
                    'name': player.name,
                    'created_at': player.created_at.isoformat() if player.created_at else None,
                    'last_used_at': player.last_used_at.isoformat() if player.last_used_at else None
                })
            
            return jsonify({
                'success': True,
                'players': players_data
            })
        except Exception as e:
            logger.error(f"Ошибка при получении списка игроков: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении списка игроков'}), 500

    @app.route('/api/players', methods=['POST'])
    def add_player():
        """Добавление нового игрока в список"""
        try:
            data = request.get_json()
            name = data.get('name', '').strip()
            
            if not name:
                return jsonify({
                    'success': False,
                    'error': 'Имя игрока не может быть пустым'
                }), 400
            
            # Проверяем, существует ли игрок с таким именем
            existing_player = Player.query.filter_by(name=name).first()
            if existing_player:
                # Обновляем время последнего использования
                existing_player.last_used_at = datetime.utcnow()
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Игрок уже существует в списке',
                    'player': {
                        'id': existing_player.id,
                        'name': existing_player.name,
                        'created_at': existing_player.created_at.isoformat() if existing_player.created_at else None,
                        'last_used_at': existing_player.last_used_at.isoformat() if existing_player.last_used_at else None
                    }
                })
            
            # Создаем нового игрока
            new_player = Player(name=name)
            db.session.add(new_player)
            db.session.commit()
            
            logger.info(f"Добавлен новый игрок: {name}")
            
            return jsonify({
                'success': True,
                'message': 'Игрок успешно добавлен в список',
                'player': {
                    'id': new_player.id,
                    'name': new_player.name,
                    'created_at': new_player.created_at.isoformat() if new_player.created_at else None,
                    'last_used_at': new_player.last_used_at.isoformat() if new_player.last_used_at else None
                }
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении игрока: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при добавлении игрока'}), 500

    @app.route('/api/players/<int:player_id>', methods=['PUT'])
    def update_player(player_id):
        """Переименование игрока"""
        try:
            data = request.get_json()
            new_name = data.get('name', '').strip()
            
            if not new_name:
                return jsonify({
                    'success': False,
                    'error': 'Имя игрока не может быть пустым'
                }), 400
            
            player = Player.query.get_or_404(player_id)
            old_name = player.name
            
            # Проверяем, не существует ли уже игрок с таким именем
            existing_player = Player.query.filter_by(name=new_name).first()
            if existing_player and existing_player.id != player_id:
                return jsonify({
                    'success': False,
                    'error': 'Игрок с таким именем уже существует'
                }), 400
            
            # Обновляем имя
            player.name = new_name
            db.session.commit()
            
            logger.info(f"Игрок переименован: '{old_name}' -> '{new_name}'")
            
            return jsonify({
                'success': True,
                'message': f'Игрок успешно переименован',
                'player': {
                    'id': player.id,
                    'name': player.name,
                    'created_at': player.created_at.isoformat() if player.created_at else None,
                    'last_used_at': player.last_used_at.isoformat() if player.last_used_at else None
                }
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при переименовании игрока: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при переименовании игрока'}), 500

    @app.route('/api/players/<int:player_id>', methods=['DELETE'])
    def delete_player(player_id):
        """Удаление игрока из списка"""
        try:
            player = Player.query.get_or_404(player_id)
            player_name = player.name
            
            db.session.delete(player)
            db.session.commit()
            
            logger.info(f"Игрок удален из списка: {player_name}")
            
            return jsonify({
                'success': True,
                'message': f'Игрок "{player_name}" удален из списка'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении игрока: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при удалении игрока'}), 500

    @app.route('/api/players/search', methods=['GET'])
    def search_players():
        """Поиск игроков по имени"""
        try:
            query = request.args.get('q', '').strip()
            if not query:
                return jsonify({
                    'success': True,
                    'players': []
                })
            
            players = Player.query.filter(Player.name.ilike(f'%{query}%')).order_by(Player.name).limit(20).all()
            players_data = []
            for player in players:
                players_data.append({
                    'id': player.id,
                    'name': player.name,
                    'created_at': player.created_at.isoformat() if player.created_at else None,
                    'last_used_at': player.last_used_at.isoformat() if player.last_used_at else None
                })
            
            return jsonify({
                'success': True,
                'players': players_data
            })
            
        except Exception as e:
            logger.error(f"Ошибка при поиске игроков: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при поиске игроков'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/status', methods=['PUT'])
    def update_tournament_status_api(tournament_id):
        """Ручное изменение статуса турнира (только для администраторов)"""
        from flask import session, request, jsonify
        import logging
        
        logger = logging.getLogger(__name__)
        
        try:
            # Проверяем авторизацию
            if 'admin_id' not in session:
                return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
            
            admin_id = session['admin_id']
            admin_email = session.get('admin_email', '')
            
            # Проверяем доступ к турниру
            tournament = Tournament.query.get_or_404(tournament_id)
            if tournament.admin_id != admin_id and admin_email != 'admin@system':
                return jsonify({'success': False, 'error': 'Нет доступа к турниру'}), 403
            
            data = request.get_json()
            if not data or 'status' not in data:
                return jsonify({'success': False, 'error': 'Необходимо указать статус'}), 400
            
            new_status = data['status']
            valid_statuses = ['регистрация', 'активен', 'завершен']
            
            if new_status not in valid_statuses:
                return jsonify({'success': False, 'error': f'Недопустимый статус. Допустимые: {", ".join(valid_statuses)}'}), 400
            
            old_status = tournament.status
            tournament.status = new_status
            db.session.commit()
            
            logger.info(f"Статус турнира {tournament_id} изменен с '{old_status}' на '{new_status}' администратором {admin_id}")
            
            return jsonify({
                'success': True, 
                'message': f'Статус турнира изменен на "{new_status}"',
                'tournament': {
                    'id': tournament.id,
                    'name': tournament.name,
                    'status': tournament.status
                }
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при изменении статуса турнира: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при изменении статуса: {str(e)}'}), 500

    # API для удаления игроков (только для системного администратора)
    @app.route('/api/admin/players/<int:player_id>', methods=['DELETE'])
    def delete_player_admin(player_id):
        """Удаление игрока из списка (только для системного администратора)"""
        from flask import session
        
        # Проверяем, что системный админ авторизован
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        admin_email = session.get('admin_email', '')
        
        # Проверяем, что это системный администратор
        if admin_email != 'admin@system':
            return jsonify({'success': False, 'error': 'Доступ запрещен. Требуются права системного администратора'}), 403
        
        try:
            # Находим игрока
            player = Player.query.get(player_id)
            if not player:
                return jsonify({'success': False, 'error': 'Игрок не найден'}), 404
            
            player_name = player.name
            
            # Удаляем игрока
            db.session.delete(player)
            db.session.commit()
            
            logger.info(f"Игрок '{player_name}' (ID: {player_id}) удален системным администратором")
            
            return jsonify({
                'success': True,
                'message': f'Игрок "{player_name}" успешно удален'
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении игрока: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при удалении игрока: {str(e)}'}), 500

    # ===== УПРАВЛЕНИЕ СЕССИЯМИ =====
    
    @app.route('/api/admin/sessions', methods=['GET'])
    def get_active_sessions():
        """Получение списка активных сессий"""
        from flask import session
        from utils.session_manager import create_session_manager
        from models import create_models
        
        # Проверяем авторизацию системного администратора
        logger.info(f"API get_active_sessions: session.get('is_system_admin') = {session.get('is_system_admin')}")
        logger.info(f"API get_active_sessions: session keys = {list(session.keys())}")
        
        if not session.get('is_system_admin'):
            logger.warning("API get_active_sessions: доступ запрещен - пользователь не системный администратор")
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
        
        try:
            models = create_models(db)
            UserActivity = models['UserActivity']
            session_manager = create_session_manager(db, UserActivity)
            
            active_sessions = session_manager.get_all_active_sessions()
            
            sessions_data = []
            for session_record in active_sessions:
                sessions_data.append({
                    'id': session_record.id,
                    'email': session_record.email,
                    'ip_address': session_record.ip_address,
                    'user_agent': session_record.user_agent,
                    'created_at': session_record.created_at.isoformat(),
                    'last_activity': session_record.last_activity.isoformat(),
                    'last_page': session_record.last_page,
                    'pages_visited_count': session_record.pages_visited_count,
                    'login_token': session_record.login_token
                })
            
            return jsonify({
                'success': True,
                'sessions': sessions_data
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении активных сессий: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/sessions/terminate', methods=['POST'])
    def terminate_session():
        """Завершение сессии администратором"""
        from flask import session
        from utils.session_manager import create_session_manager
        from models import create_models
        
        # Проверяем авторизацию системного администратора
        if not session.get('is_system_admin'):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
        
        data = request.get_json()
        if not data or not data.get('email'):
            return jsonify({'success': False, 'error': 'Не указан email пользователя'}), 400
        
        try:
            models = create_models(db)
            UserActivity = models['UserActivity']
            session_manager = create_session_manager(db, UserActivity)
            
            admin_email = session.get('admin_email', 'admin@system')
            success = session_manager.terminate_session_by_admin(data['email'], admin_email, 'forced')
            
            if success:
                logger.info(f"Сессия пользователя {data['email']} завершена администратором {admin_email}")
                return jsonify({
                    'success': True,
                    'message': f'Сессия пользователя {data["email"]} успешно завершена'
                })
            else:
                return jsonify({'success': False, 'error': 'Ошибка при завершении сессии'}), 500
                
        except Exception as e:
            logger.error(f"Ошибка при завершении сессии: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/sessions/history', methods=['GET'])
    def get_session_history():
        """Получение истории сессий"""
        from flask import session
        from utils.session_manager import create_session_manager
        from models import create_models
        from datetime import datetime, timedelta
        
        # Проверяем авторизацию системного администратора
        if not session.get('is_system_admin'):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
        
        try:
            models = create_models(db)
            UserActivity = models['UserActivity']
            session_manager = create_session_manager(db, UserActivity)
            
            # Получаем параметры фильтрации
            email = request.args.get('email')
            date_from_str = request.args.get('date_from')
            date_to_str = request.args.get('date_to')
            limit = int(request.args.get('limit', 100))
            
            date_from = None
            date_to = None
            
            if date_from_str:
                date_from = datetime.fromisoformat(date_from_str)
            if date_to_str:
                date_to = datetime.fromisoformat(date_to_str)
            
            # Если не указаны даты, берем последние 30 дней
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            history = session_manager.get_session_history(email, date_from, date_to, limit)
            
            sessions_data = []
            for session_record in history:
                sessions_data.append({
                    'id': session_record.id,
                    'email': session_record.email,
                    'ip_address': session_record.ip_address,
                    'created_at': session_record.created_at.isoformat(),
                    'terminated_at': session_record.terminated_at.isoformat() if session_record.terminated_at else None,
                    'session_duration': session_record.session_duration,
                    'logout_reason': session_record.logout_reason,
                    'pages_visited_count': session_record.pages_visited_count,
                    'last_page': session_record.last_page,
                    'is_terminated': session_record.is_terminated,
                    'terminated_by': session_record.terminated_by
                })
            
            return jsonify({
                'success': True,
                'sessions': sessions_data
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории сессий: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/sessions/statistics', methods=['GET'])
    def get_session_statistics():
        """Получение статистики по сессиям"""
        from flask import session
        from utils.session_analytics import create_session_analytics
        from models import create_models
        from datetime import datetime, timedelta
        from sqlalchemy import or_
        
        # Проверяем авторизацию системного администратора
        if not session.get('is_system_admin'):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
        
        try:
            models = create_models(db)
            UserActivity = models['UserActivity']
            analytics = create_session_analytics(db, UserActivity)
            
            # Получаем параметры фильтрации
            date_from_str = request.args.get('date_from')
            date_to_str = request.args.get('date_to')
            
            date_from = None
            date_to = None
            
            if date_from_str:
                date_from = datetime.fromisoformat(date_from_str)
            if date_to_str:
                date_to = datetime.fromisoformat(date_to_str)
            
            # Если не указаны даты, берем последние 30 дней
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            # Получаем различные виды статистики
            overall_stats = analytics.get_overall_statistics(date_from, date_to)
            hourly_stats = analytics.get_peak_hours_stats(date_from, date_to)
            termination_stats = analytics.get_termination_reasons_stats(date_from, date_to)
            duration_stats = analytics.get_session_duration_stats(date_from, date_to)
            
            # Получаем количество активных сессий (используем те же критерии, что и в таблице)
            active_sessions_count = UserActivity.query.filter(
                UserActivity.user_type == 'admin',
                UserActivity.is_active == True,
                UserActivity.is_terminated == False,
                or_(
                    UserActivity.expires_at.is_(None),
                    UserActivity.expires_at > datetime.utcnow()
                )
            ).count()
            
            # Получаем количество подключенных администраторов турниров (исключая системного администратора)
            tournament_admins_count = UserActivity.query.filter(
                UserActivity.user_type == 'admin',
                UserActivity.is_active == True,
                UserActivity.is_terminated == False,
                UserActivity.email != 'admin@system',
                or_(
                    UserActivity.expires_at.is_(None),
                    UserActivity.expires_at > datetime.utcnow()
                )
            ).count()
            
            # Добавляем количество активных сессий в статистику
            overall_stats['active_sessions'] = active_sessions_count
            overall_stats['tournament_admins_online'] = tournament_admins_count
            
            return jsonify({
                'success': True,
                'stats': overall_stats,
                'hourly_stats': hourly_stats,
                'termination_stats': termination_stats,
                'duration_stats': duration_stats
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики сессий: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/sessions/cleanup', methods=['POST'])
    def cleanup_sessions():
        """Принудительная очистка истекших сессий"""
        from flask import session
        from utils.session_manager import create_session_manager
        from models import create_models
        
        # Проверяем авторизацию системного администратора
        if not session.get('is_system_admin'):
            return jsonify({'success': False, 'error': 'Доступ запрещен'}), 403
        
        try:
            models = create_models(db)
            UserActivity = models['UserActivity']
            session_manager = create_session_manager(db, UserActivity)
            
            cleaned_count = session_manager.cleanup_expired_sessions()
            
            return jsonify({
                'success': True,
                'message': f'Очищено {cleaned_count} истекших сессий',
                'cleaned_count': cleaned_count
            })
            
        except Exception as e:
            logger.error(f"Ошибка при очистке сессий: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/referee/generate', methods=['POST'])
    def generate_referee_html():
        """Генерирует HTML для приложения Referee с заполненными именами участников"""
        try:
            data = request.get_json()
            participant1_name = data.get('participant1', 'Игрок 1')
            participant2_name = data.get('participant2', 'Игрок 2')
            tournament_name = data.get('tournament_name', 'Турнир')
            
            # Импортируем утилиту для генерации HTML
            from utils.referee_utils import generate_referee_html
            
            # Генерируем HTML с заполненными именами
            html_content = generate_referee_html(participant1_name, participant2_name, tournament_name)
            
            return jsonify({
                'success': True,
                'html': html_content
            })
            
        except Exception as e:
            logger.error(f"Ошибка при генерации HTML для Referee: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/matches/<int:match_id>/auto-save-score', methods=['POST'])
    def auto_save_match_score(match_id):
        """Автоматическое сохранение счета матча (используется страницей судейства)"""
        from flask import session
        from datetime import datetime
        try:
            # CSRF из заголовка, аналогично другим POST API
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'Отсутствует CSRF токен'}), 400
            
            # Проверяем CSRF токен
            try:
                from flask_wtf.csrf import validate_csrf
                validate_csrf(csrf_token)
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем данные из запроса
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Отсутствуют данные'}), 400
            
            score1 = data.get('score1', 0)
            score2 = data.get('score2', 0)
            set_number = data.get('set_number', 1)
            
            # Находим матч
            match = Match.query.get(match_id)
            if not match:
                return jsonify({'success': False, 'error': 'Матч не найден'}), 404
            
            # Обновляем счет в соответствующем сете
            if set_number == 1:
                match.set1_score1 = score1
                match.set1_score2 = score2
            elif set_number == 2:
                match.set2_score1 = score1
                match.set2_score2 = score2
            elif set_number == 3:
                match.set3_score1 = score1
                match.set3_score2 = score2
            
            # Устанавливаем реальное время начала матча при первом сохранении счета
            # Используем локальное время для учета часового пояса пользователя
            if not match.actual_start_time:
                match.actual_start_time = datetime.now()
                match.status = 'в_процессе'
                logger.info(f"[РЕАЛЬНОЕ ВРЕМЯ] Начало матча {match_id} (первое действие): {match.actual_start_time}")
            
            # Обновляем время последнего изменения
            match.updated_at = datetime.now()
            
            # Сохраняем изменения
            db.session.commit()
            
            logger.info(f"Автоматически сохранен счет для матча {match_id}, сет {set_number}: {score1}:{score2}")
            return jsonify({'success': True, 'message': f'Счет сохранен: {score1}:{score2}'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при автосохранении счета матча {match_id}: {str(e)}")
            return jsonify({'success': False, 'error': f'Ошибка при сохранении счета: {str(e)}'}), 500

    @app.route('/api/match-log/add', methods=['POST'])
    def add_match_log_entry():
        """Добавление записи в журнал матча (используется страницей судейства)"""
        from flask import session
        try:
            # CSRF из заголовка, аналогично другим POST API
            from flask_wtf.csrf import validate_csrf
            validate_csrf(request.headers.get('X-CSRFToken'))
        except Exception as e:
            logger.warning(f"CSRF validation failed (match-log add): {e}")
            return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400

        # Простая проверка авторизации администратора турнира
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401

        data = request.get_json() or {}
        logger.info(f"API: Получены данные журнала: {data}")

        required_fields = [
            'tournament_id', 'match_id', 'set_number',
            'previous_score_left', 'previous_score_right',
            'current_score_left', 'current_score_right',
            'serve_position', 'left_player_name', 'right_player_name',
            'action'
        ]
        missing = [f for f in required_fields if f not in data]
        if missing:
            return jsonify({'success': False, 'error': f'Отсутствуют поля: {", ".join(missing)}'}), 400

        try:
            # Импортируем модель отложенно, чтобы избегать циклических импортов
            from models.match_log import MatchLog

            entry = MatchLog(
                tournament_id=int(data['tournament_id']),
                match_id=int(data['match_id']),
                set_number=int(data['set_number']),
                previous_score_left=int(data['previous_score_left']),
                previous_score_right=int(data['previous_score_right']),
                current_score_left=int(data['current_score_left']),
                current_score_right=int(data['current_score_right']),
                serve_position=str(data['serve_position']),
                left_player_name=str(data['left_player_name']),
                right_player_name=str(data['right_player_name']),
                action=str(data['action']),
                notes=str(data.get('notes') or '')
            )

            db.session.add(entry)
            db.session.commit()
            logger.info(f"API: Запись журнала создана с ID: {entry.id}")
            return jsonify({'success': True, 'id': entry.id}), 200

        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при добавлении записи журнала: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при добавлении записи журнала'}), 500

    @app.route('/api/matches/<int:match_id>/save-referee-result', methods=['POST'])
    def save_referee_result(match_id):
        """Сохранение результата матча из страницы судейства"""
        from flask import session
        from datetime import datetime
        try:
            # CSRF из заголовка
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'Отсутствует CSRF токен'}), 400
            
            # Проверяем CSRF токен
            try:
                from flask_wtf.csrf import validate_csrf
                validate_csrf(csrf_token)
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем данные из запроса
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Отсутствуют данные'}), 400
            
            # Находим матч
            match = Match.query.get(match_id)
            if not match:
                return jsonify({'success': False, 'error': 'Матч не найден'}), 404
            
            # Получаем турнир для настроек
            tournament = Tournament.query.get(match.tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Обновляем результаты матча
            sets_data = data.get('sets', [])
            sets_won_1 = 0
            sets_won_2 = 0
            
            # Логируем полученные данные для диагностики
            logger.info(f"[save-referee-result] Матч {match_id}: получены данные sets_data = {sets_data}")
            logger.info(f"[save-referee-result] Матч {match_id}: полный data = {data}")
            
            # Обрабатываем каждый сет
            for set_data in sets_data:
                set_number = set_data.get('set_number', 1)
                score1 = set_data.get('score1', 0)
                score2 = set_data.get('score2', 0)
                completed = set_data.get('completed', False)
                
                logger.info(f"[save-referee-result] Обработка сета {set_number}: score1={score1}, score2={score2}, completed={completed}")
                
                # Сохраняем счет сета
                if set_number == 1:
                    match.set1_score1 = score1
                    match.set1_score2 = score2
                elif set_number == 2:
                    match.set2_score1 = score1
                    match.set2_score2 = score2
                elif set_number == 3:
                    match.set3_score1 = score1
                    match.set3_score2 = score2
                
                # Определяем победителя сета в зависимости от вида спорта
                sport_type = tournament.sport_type.lower() if tournament.sport_type else ''
                
                if 'пинг-понг' in sport_type or 'настольный теннис' in sport_type or 'pingpong' in sport_type:
                    # Правила пинг-понга: 11 очков и разница >= 2
                    min_score = 11
                elif 'бадминтон' in sport_type or 'badminton' in sport_type:
                    # Правила бадминтона: 21 очко и разница >= 2, либо 30 очков (независимо от счёта соперника)
                    min_score = 21
                    max_score = 30  # Максимальный счёт - победа при достижении 30 очков
                    
                    logger.info(f"[save-referee-result] Сет {set_number}: sport_type={sport_type}, min_score={min_score}, max_score={max_score}, проверка победителя...")
                    
                    # Специальное условие: если одна сторона набрала 30 очков - победа
                    # (независимо от счёта соперника, который может быть 29 или 28)
                    if score1 >= max_score:
                        sets_won_1 += 1
                        logger.info(f"[save-referee-result] Сет {set_number}: победила команда 1 по правилу 30 очков (счёт: {score1}:{score2}), sets_won_1={sets_won_1}")
                    elif score2 >= max_score:
                        sets_won_2 += 1
                        logger.info(f"[save-referee-result] Сет {set_number}: победила команда 2 по правилу 30 очков (счёт: {score1}:{score2}), sets_won_2={sets_won_2}")
                    # Обычное условие: 21 очко и разница >= 2
                    elif score1 >= min_score and score1 - score2 >= 2:
                        sets_won_1 += 1
                        logger.info(f"[save-referee-result] Сет {set_number}: победила команда 1 (счёт: {score1}:{score2}), sets_won_1={sets_won_1}")
                    elif score2 >= min_score and score2 - score1 >= 2:
                        sets_won_2 += 1
                        logger.info(f"[save-referee-result] Сет {set_number}: победила команда 2 (счёт: {score1}:{score2}), sets_won_2={sets_won_2}")
                    else:
                        logger.info(f"[save-referee-result] Сет {set_number}: не завершен (score1={score1}, score2={score2}, min_score={min_score})")
                else:
                    # Правила волейбола: 25 очков (или 15 для 3-го сета) и разница >= 2
                    min_score = 15 if (set_number == 3 and tournament.sets_to_win == 2) else 25
                    
                    logger.info(f"[save-referee-result] Сет {set_number}: sport_type={sport_type}, min_score={min_score}, проверка победителя...")
                    
                    if score1 >= min_score and score1 - score2 >= 2:
                        sets_won_1 += 1
                        logger.info(f"[save-referee-result] Сет {set_number}: победила команда 1, sets_won_1={sets_won_1}")
                    elif score2 >= min_score and score2 - score1 >= 2:
                        sets_won_2 += 1
                        logger.info(f"[save-referee-result] Сет {set_number}: победила команда 2, sets_won_2={sets_won_2}")
                    else:
                        logger.info(f"[save-referee-result] Сет {set_number}: не завершен (score1={score1}, score2={score2}, min_score={min_score})")
            
            # Сохраняем количество выигранных сетов
            match.sets_won_1 = sets_won_1
            match.sets_won_2 = sets_won_2
            
            # Определяем победителя матча
            sets_to_win = tournament.sets_to_win if tournament.sets_to_win else 2
            if sets_won_1 >= sets_to_win:
                match.winner_id = match.participant1_id
                match.status = 'завершен'
            elif sets_won_2 >= sets_to_win:
                match.winner_id = match.participant2_id
                match.status = 'завершен'
            else:
                match.winner_id = None
                match.status = 'в_процессе'
            
            # Сохраняем общий результат в формате "2:1"
            match.score = f"{sets_won_1}:{sets_won_2}"
            
            logger.info(f"[save-referee-result] ПЕРЕД commit: set1=({match.set1_score1}:{match.set1_score2}), set2=({match.set2_score1}:{match.set2_score2}), set3=({match.set3_score1}:{match.set3_score2})")
            
            # Сохраняем изменения
            db.session.commit()
            
            logger.info(f"[save-referee-result] ПОСЛЕ commit: set1=({match.set1_score1}:{match.set1_score2}), set2=({match.set2_score1}:{match.set2_score2}), set3=({match.set3_score1}:{match.set3_score2})")
            
            # Проверяем, что данные действительно сохранились
            match_check = Match.query.get(match_id)
            logger.info(f"[save-referee-result] Проверка из БД после commit: set1=({match_check.set1_score1}:{match_check.set1_score2}), set2=({match_check.set2_score1}:{match_check.set2_score2}), set3=({match_check.set3_score1}:{match_check.set3_score2})")
            
            # Если матч завершен, устанавливаем реальное время окончания и пересчитываем расписание
            # Используем локальное время для учета часового пояса пользователя
            if match.status == 'завершен':
                logger.info(f"[save-referee-result] Матч {match_id} завершен, начинаем пересчет расписания")
                if not match.actual_end_time:
                    match.actual_end_time = datetime.now()
                    db.session.commit()
                
                # Пересчитываем время следующих матчей на той же площадке
                try:
                    # Tournament и Match уже доступны в области видимости функции create_api_routes
                    logger.info(f"[save-referee-result] Вызов функции пересчета для матча {match_id}")
                    recalculate_schedule_after_match_completion(match_id, Tournament, Match, db)
                    logger.info(f"[save-referee-result] Функция пересчета завершена для матча {match_id}")
                except Exception as e:
                    logger.error(f"[save-referee-result] Ошибка при пересчете расписания после завершения матча {match_id}: {e}", exc_info=True)
            
            # Обновляем статус турнира
            participants = Participant.query.filter_by(tournament_id=tournament.id).all()
            matches = Match.query.filter_by(tournament_id=tournament.id).all()
            update_tournament_status(tournament, participants, matches, db)
            
            # Еще одна проверка ПОСЛЕ update_tournament_status
            match_final = Match.query.get(match_id)
            logger.info(f"[save-referee-result] Финальная проверка: set1=({match_final.set1_score1}:{match_final.set1_score2}), set2=({match_final.set2_score1}:{match_final.set2_score2}), set3=({match_final.set3_score1}:{match_final.set3_score2})")
            
            logger.info(f"Результат матча {match_id} сохранен из судейства: {match.score}")
            return jsonify({'success': True, 'message': 'Результат сохранен'}), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при сохранении результата из судейства: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при сохранении результата'}), 500

    @app.route('/api/tournaments/<int:tournament_id>/matches/<int:match_id>/invite', methods=['POST'])
    def invite_participants_to_match(tournament_id, match_id):
        """Отправка приглашений участникам матча в Telegram"""
        from flask import session
        try:
            # Проверяем права доступа
            session_admin_id = session.get('admin_id')
            if not session_admin_id:
                return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
            
            # Проверяем CSRF токен
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'Отсутствует CSRF токен'}), 400
            
            try:
                from flask_wtf.csrf import validate_csrf
                validate_csrf(csrf_token)
            except Exception as e:
                logger.warning(f"CSRF validation failed: {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем данные из запроса
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Отсутствуют данные'}), 400
            
            # Получаем турнир
            tournament = Tournament.query.get(tournament_id)
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Получаем матч
            match = Match.query.get(match_id)
            if not match:
                return jsonify({'success': False, 'error': 'Матч не найден'}), 404
            
            # Проверяем, что матч принадлежит турниру
            if match.tournament_id != tournament_id:
                return jsonify({'success': False, 'error': 'Матч не принадлежит данному турниру'}), 400
            
            participant1_name = data.get('participant1_name', '')
            participant2_name = data.get('participant2_name', '')
            match_time = data.get('match_time', '')
            match_court = data.get('match_court', 0)
            
            # Находим участников по именам
            participant1 = Participant.query.filter_by(tournament_id=tournament_id, name=participant1_name).first()
            participant2 = Participant.query.filter_by(tournament_id=tournament_id, name=participant2_name).first()
            
            sent = []
            not_found = []
            failed = []
            
            # Формируем информацию о площадке
            court_info = f"Площадка {match_court}" if match_court > 0 else "Площадка не указана"
            
            # Отправляем приглашение первому участнику
            if participant1:
                if participant1.telegram:
                    message = f"""🏓 <b>Приглашение на матч!</b>

📅 Турнир: <b>{tournament.name}</b>
⏰ Время: <b>{match_time}</b>
📍 {court_info}

🎯 <b>Ваш соперник:</b> {participant2_name}

Удачи в матче! 🏆"""
                    
                    try:
                        success = send_telegram_message(message, telegram_contact=participant1.telegram)
                        if success:
                            sent.append(participant1_name)
                            logger.info(f"✅ Приглашение отправлено участнику {participant1_name} (Telegram: {participant1.telegram})")
                        else:
                            failed.append(participant1_name)
                            logger.warning(f"⚠️ Не удалось отправить приглашение участнику {participant1_name}")
                    except Exception as e:
                        failed.append(participant1_name)
                        logger.error(f"❌ Ошибка при отправке приглашения участнику {participant1_name}: {e}")
                else:
                    not_found.append(participant1_name)
                    logger.info(f"ℹ️  Telegram не указан для участника {participant1_name}")
            else:
                not_found.append(participant1_name)
                logger.warning(f"⚠️  Участник {participant1_name} не найден в турнире")
            
            # Отправляем приглашение второму участнику
            if participant2:
                if participant2.telegram:
                    message = f"""🏓 <b>Приглашение на матч!</b>

📅 Турнир: <b>{tournament.name}</b>
⏰ Время: <b>{match_time}</b>
📍 {court_info}

🎯 <b>Ваш соперник:</b> {participant1_name}

Удачи в матче! 🏆"""
                    
                    try:
                        success = send_telegram_message(message, telegram_contact=participant2.telegram)
                        if success:
                            sent.append(participant2_name)
                            logger.info(f"✅ Приглашение отправлено участнику {participant2_name} (Telegram: {participant2.telegram})")
                        else:
                            failed.append(participant2_name)
                            logger.warning(f"⚠️ Не удалось отправить приглашение участнику {participant2_name}")
                    except Exception as e:
                        failed.append(participant2_name)
                        logger.error(f"❌ Ошибка при отправке приглашения участнику {participant2_name}: {e}")
                else:
                    not_found.append(participant2_name)
                    logger.info(f"ℹ️  Telegram не указан для участника {participant2_name}")
            else:
                not_found.append(participant2_name)
                logger.warning(f"⚠️  Участник {participant2_name} не найден в турнире")
            
            return jsonify({
                'success': True,
                'sent': sent,
                'not_found': not_found,
                'failed': failed
            })
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при отправке приглашений участникам матча: {e}")
            return jsonify({'success': False, 'error': f'Ошибка при отправке приглашений: {str(e)}'}), 500
    
    @app.route('/api/tournaments/<int:tournament_id>/updates', methods=['GET'])
    def tournament_updates(tournament_id):
        """API для частичного обновления данных турнира (только счёт матчей и статистика)"""
        try:
            tournament = Tournament.query.get_or_404(tournament_id)
            
            # Получаем участников турнира
            participants = Participant.query.filter_by(tournament_id=tournament_id).order_by(Participant.name).all()
            
            # Получаем матчи турнира
            matches = Match.query.filter_by(tournament_id=tournament_id).order_by(Match.match_date, Match.match_time).all()
            
            # Дедупликация матчей
            seen_matches = set()
            unique_matches = []
            for match in matches:
                match_key = (match.participant1_id, match.participant2_id, match.match_date, match.match_time)
                if match_key not in seen_matches:
                    seen_matches.add(match_key)
                    unique_matches.append(match)
            matches = unique_matches
            
            # Подготавливаем данные матчей для отправки
            matches_data = []
            for match in matches:
                participant1 = Participant.query.get(match.participant1_id)
                participant2 = Participant.query.get(match.participant2_id)
                
                # Формируем счёт
                score = None
                sets_details = None
                
                # Проверяем, есть ли счёт по сетам (sets_won_1, sets_won_2) или по текущим сетам
                if match.status in ['завершен', 'в_процессе', 'играют']:
                    # Сначала проверяем sets_won_1 и sets_won_2 (основной счёт)
                    if match.sets_won_1 is not None and match.sets_won_2 is not None:
                        score = f"{match.sets_won_1}:{match.sets_won_2}"
                    # Если основного счёта нет, но есть счёт в текущем сете, формируем временный счёт
                    elif match.status in ['в_процессе', 'играют']:
                        # Подсчитываем выигранные сеты на основе завершенных сетов
                        sets_won_1 = 0
                        sets_won_2 = 0
                        points_to_win = tournament.points_to_win or 21
                        
                        # Проверяем каждый сет
                        if match.set1_score1 is not None and match.set1_score2 is not None:
                            if match.set1_score1 >= points_to_win and match.set1_score1 > match.set1_score2:
                                sets_won_1 += 1
                            elif match.set1_score2 >= points_to_win and match.set1_score2 > match.set1_score1:
                                sets_won_2 += 1
                        
                        if match.set2_score1 is not None and match.set2_score2 is not None:
                            if match.set2_score1 >= points_to_win and match.set2_score1 > match.set2_score2:
                                sets_won_1 += 1
                            elif match.set2_score2 >= points_to_win and match.set2_score2 > match.set2_score1:
                                sets_won_2 += 1
                        
                        if match.set3_score1 is not None and match.set3_score2 is not None:
                            if match.set3_score1 >= points_to_win and match.set3_score1 > match.set3_score2:
                                sets_won_1 += 1
                            elif match.set3_score2 >= points_to_win and match.set3_score2 > match.set3_score1:
                                sets_won_2 += 1
                        
                        # Если есть хотя бы один завершенный сет, показываем счёт
                        if sets_won_1 > 0 or sets_won_2 > 0:
                            score = f"{sets_won_1}:{sets_won_2}"
                    
                    # Детали сетов (показываем все сеты, которые начались)
                    if score:
                        sets_list = []
                        points_to_win = tournament.points_to_win or 21
                        if match.set1_score1 is not None and match.set1_score2 is not None and (match.set1_score1 > 0 or match.set1_score2 > 0) and not (match.set1_score1 == 0 and match.set1_score2 == 0) and not (match.set1_score1 == points_to_win and match.set1_score2 == points_to_win):
                            sets_list.append(f"{match.set1_score1}:{match.set1_score2}")
                        if match.set2_score1 is not None and match.set2_score2 is not None and (match.set2_score1 > 0 or match.set2_score2 > 0) and not (match.set2_score1 == 0 and match.set2_score2 == 0) and not (match.set2_score1 == points_to_win and match.set2_score2 == points_to_win):
                            sets_list.append(f"{match.set2_score1}:{match.set2_score2}")
                        if match.set3_score1 is not None and match.set3_score2 is not None and (match.set3_score1 > 0 or match.set3_score2 > 0) and not (match.set3_score1 == 0 and match.set3_score2 == 0) and not (match.set3_score1 == points_to_win and match.set3_score2 == points_to_win):
                            sets_list.append(f"{match.set3_score1}:{match.set3_score2}")
                        if sets_list:
                            sets_details = ", ".join(sets_list)
                
                matches_data.append({
                    'id': match.id,
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id,
                    'participant1_name': participant1.name if participant1 else '',
                    'participant2_name': participant2.name if participant2 else '',
                    'score': score,
                    'sets_details': sets_details,
                    'status': match.status,
                    'match_date': match.match_date.strftime('%Y-%m-%d') if match.match_date else None,
                    'match_time': match.match_time.strftime('%H:%M') if match.match_time else None,
                    'set1_score1': match.set1_score1,
                    'set1_score2': match.set1_score2,
                    'set2_score1': match.set2_score1,
                    'set2_score2': match.set2_score2,
                    'set3_score1': match.set3_score1,
                    'set3_score2': match.set3_score2,
                    'sets_won_1': match.sets_won_1,
                    'sets_won_2': match.sets_won_2
                })
            
            # Подсчитываем статистику участников (используем логику из tournament_spectator)
            from routes.main import calculate_participant_ranking
            final_ranking = calculate_participant_ranking(participants, matches, tournament)
            
            # Создаем словарь для быстрого поиска
            ranking_data_by_id = {}
            for p_data in final_ranking:
                ranking_data_by_id[p_data['participant'].id] = p_data
            
            # Формируем статистику участников
            participants_stats = []
            for participant in participants:
                ranking_data = ranking_data_by_id.get(participant.id, {})
                participants_stats.append({
                    'id': participant.id,
                    'name': participant.name,
                    'position': ranking_data.get('place', 999),
                    'points': ranking_data.get('points', 0),
                    'wins': ranking_data.get('wins', 0),
                    'losses': ranking_data.get('losses', 0),
                    'draws': ranking_data.get('draws', 0),
                    'games': ranking_data.get('games', 0),
                    'sets_difference': ranking_data.get('sets_won', 0) - ranking_data.get('sets_lost', 0),
                    'goal_difference': ranking_data.get('set_difference', 0)
                })
            
            # Сортируем по позиции
            participants_stats.sort(key=lambda x: x['position'])
            
            return jsonify({
                'success': True,
                'matches': matches_data,
                'participants_stats': participants_stats
            })
            
        except Exception as e:
            logger.error(f"Ошибка при получении обновлений турнира {tournament_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500

    # ===== РОЗЫГРЫШИ БАДМИНТОНА =====
    
    @app.route('/api/rallies', methods=['POST'])
    def create_rally():
        """Создание нового розыгрыша для бадминтона"""
        try:
            # CSRF из заголовка
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'Отсутствует CSRF токен'}), 400
            
            # Проверяем CSRF токен
            try:
                from flask_wtf.csrf import validate_csrf
                validate_csrf(csrf_token)
            except Exception as e:
                logger.warning(f"CSRF validation failed (rally create): {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            # Получаем данные из запроса
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'error': 'Отсутствуют данные'}), 400
            
            # Проверяем обязательные поля
            required_fields = ['match_id', 'tournament_id', 'set_number', 'server_name', 'receiver_name', 'server_won', 'score']
            missing = [f for f in required_fields if f not in data]
            if missing:
                return jsonify({'success': False, 'error': f'Отсутствуют обязательные поля: {", ".join(missing)}'}), 400
            
            # Проверяем, что матч существует
            match = Match.query.get(data['match_id'])
            if not match:
                return jsonify({'success': False, 'error': 'Матч не найден'}), 404
            
            # Проверяем, что турнир существует
            tournament = Tournament.query.get(data['tournament_id'])
            if not tournament:
                return jsonify({'success': False, 'error': 'Турнир не найден'}), 404
            
            # Проверяем, что это бадминтон
            sport_type = tournament.sport_type.lower()
            if 'бадминтон' not in sport_type and 'badminton' not in sport_type:
                return jsonify({'success': False, 'error': 'Розыгрыши можно сохранять только для бадминтона'}), 400
            
            # Создаем розыгрыш
            rally_datetime = datetime.now()
            rally = Rally(
                match_id=int(data['match_id']),
                tournament_id=int(data['tournament_id']),
                set_number=int(data['set_number']),
                rally_date=rally_datetime.date(),
                rally_time=rally_datetime.time(),
                rally_datetime=rally_datetime,
                court_number=data.get('court_number'),  # опционально
                server_name=str(data['server_name']),
                receiver_name=str(data['receiver_name']),
                server_won=bool(data['server_won']),
                score=str(data['score']),
                notes=data.get('notes')  # опционально
            )
            
            db.session.add(rally)
            db.session.commit()
            
            logger.info(f"Создан розыгрыш {rally.id} для матча {data['match_id']}, сет {data['set_number']}")
            return jsonify({'success': True, 'rally': rally.to_dict()}), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при создании розыгрыша: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'error': f'Ошибка при создании розыгрыша: {str(e)}'}), 500
    
    @app.route('/api/matches/<int:match_id>/rallies', methods=['GET'])
    def get_match_rallies(match_id):
        """Получение всех розыгрышей для матча"""
        try:
            # Проверяем, что матч существует
            match = Match.query.get(match_id)
            if not match:
                return jsonify({'success': False, 'error': 'Матч не найден'}), 404
            
            # Получаем параметры запроса
            set_number = request.args.get('set_number', type=int)
            
            # Запрос розыгрышей
            query = Rally.query.filter_by(match_id=match_id)
            if set_number:
                query = query.filter_by(set_number=set_number)
            
            rallies = query.order_by(Rally.rally_datetime.asc()).all()
            
            return jsonify({
                'success': True,
                'match_id': match_id,
                'rallies': [rally.to_dict() for rally in rallies],
                'count': len(rallies)
            }), 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении розыгрышей матча {match_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/rallies/<int:rally_id>', methods=['GET'])
    def get_rally(rally_id):
        """Получение конкретного розыгрыша"""
        try:
            rally = Rally.query.get(rally_id)
            if not rally:
                return jsonify({'success': False, 'error': 'Розыгрыш не найден'}), 404
            
            return jsonify({
                'success': True,
                'rally': rally.to_dict()
            }), 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении розыгрыша {rally_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/rallies/<int:rally_id>', methods=['DELETE'])
    def delete_rally(rally_id):
        """Удаление розыгрыша"""
        try:
            # CSRF из заголовка
            csrf_token = request.headers.get('X-CSRFToken')
            if not csrf_token:
                return jsonify({'success': False, 'error': 'Отсутствует CSRF токен'}), 400
            
            # Проверяем CSRF токен
            try:
                from flask_wtf.csrf import validate_csrf
                validate_csrf(csrf_token)
            except Exception as e:
                logger.warning(f"CSRF validation failed (rally delete): {e}")
                return jsonify({'success': False, 'error': 'Неверный CSRF токен'}), 400
            
            rally = Rally.query.get(rally_id)
            if not rally:
                return jsonify({'success': False, 'error': 'Розыгрыш не найден'}), 404
            
            db.session.delete(rally)
            db.session.commit()
            
            logger.info(f"Удален розыгрыш {rally_id}")
            return jsonify({'success': True, 'message': 'Розыгрыш удален'}), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при удалении розыгрыша {rally_id}: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/admin/rallies', methods=['GET'])
    def admin_get_all_rallies():
        """Получение всех розыгрышей для администратора, сгруппированных по матчам"""
        from flask import session
        from collections import defaultdict
        
        # Проверяем авторизацию администратора
        if 'admin_id' not in session:
            return jsonify({'success': False, 'error': 'Необходима авторизация'}), 401
        
        try:
            # Получаем все розыгрыши с информацией о матчах и турнирах
            rallies = Rally.query.order_by(Rally.rally_datetime.desc()).all()
            
            # Группируем розыгрыши по match_id
            matches_dict = defaultdict(lambda: {
                'match_id': None,
                'tournament_id': None,
                'tournament_name': '',
                'rallies': [],
                'first_rally_datetime': None,
                'participants': set(),
                'final_score': None
            })
            
            for rally in rallies:
                match_id = rally.match_id
                match = Match.query.get(match_id)
                tournament = Tournament.query.get(rally.tournament_id) if rally.tournament_id else None
                
                if match_id not in matches_dict:
                    matches_dict[match_id]['match_id'] = match_id
                    matches_dict[match_id]['tournament_id'] = rally.tournament_id
                    matches_dict[match_id]['tournament_name'] = tournament.name if tournament else 'Неизвестный турнир'
                    matches_dict[match_id]['first_rally_datetime'] = rally.rally_datetime
                
                # Добавляем розыгрыш
                rally_data = {
                    'id': rally.id,
                    'set_number': rally.set_number,
                    'server_name': rally.server_name,
                    'receiver_name': rally.receiver_name,
                    'server_won': rally.server_won,
                    'score': rally.score,
                    'rally_datetime': rally.rally_datetime.isoformat() if rally.rally_datetime else None
                }
                matches_dict[match_id]['rallies'].append(rally_data)
                
                # Собираем имена участников
                if rally.server_name:
                    matches_dict[match_id]['participants'].add(rally.server_name.split(' - ')[0].split(' (')[0])
                if rally.receiver_name:
                    matches_dict[match_id]['participants'].add(rally.receiver_name.split(' - ')[0].split(' (')[0])
                
                # Обновляем финальный счёт (последний розыгрыш)
                if not matches_dict[match_id]['final_score']:
                    matches_dict[match_id]['final_score'] = rally.score
            
            # Преобразуем в список и сортируем по дате первого розыгрыша
            matches_data = []
            for match_id, match_data in matches_dict.items():
                match = Match.query.get(match_id)
                
                # Получаем имена участников из матча
                participant1_name = match.participant1.name if match and match.participant1 else None
                participant2_name = match.participant2.name if match and match.participant2 else None
                
                # Формируем строку участников в формате "имя1, имя2 - имя3, имя4"
                # Если участник - команда (содержит " - "), разбиваем на отдельных игроков
                participants_str = 'Не указаны'
                if participant1_name and participant2_name:
                    # Разбиваем имена участников (могут быть команды)
                    team1_players = [p.strip() for p in participant1_name.split(' - ')] if ' - ' in participant1_name else [participant1_name]
                    team2_players = [p.strip() for p in participant2_name.split(' - ')] if ' - ' in participant2_name else [participant2_name]
                    
                    # Формируем строку: "имя1, имя2 - имя3, имя4"
                    team1_str = ', '.join(team1_players)
                    team2_str = ', '.join(team2_players)
                    participants_str = f'{team1_str} - {team2_str}'
                elif participant1_name or participant2_name:
                    # Если только один участник указан
                    participants_str = participant1_name or participant2_name or 'Не указаны'
                
                matches_data.append({
                    'match_id': match_id,
                    'tournament_id': match_data['tournament_id'],
                    'tournament_name': match_data['tournament_name'],
                    'rally_datetime': match_data['first_rally_datetime'].isoformat() if match_data['first_rally_datetime'] else None,
                    'participants': participants_str,
                    'final_score': match_data['final_score'] or '0:0',
                    'rallies_count': len(match_data['rallies']),
                    'rallies': match_data['rallies']  # Все розыгрыши для выгрузки
                })
            
            # Сортируем по дате (новые первыми)
            matches_data.sort(key=lambda x: x['rally_datetime'] or '', reverse=True)
            
            return jsonify({'success': True, 'matches': matches_data}), 200
            
        except Exception as e:
            logger.error(f"Ошибка при получении розыгрышей: {e}")
            return jsonify({'success': False, 'error': 'Ошибка при получении розыгрышей'}), 500