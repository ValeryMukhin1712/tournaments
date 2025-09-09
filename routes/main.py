"""
Основные маршруты приложения
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def create_main_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog):
    """Создает основные маршруты приложения"""
    
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
        if current_user.role != 'администратор':
            flash('У вас нет прав для доступа к этой странице', 'error')
            return redirect(url_for('index'))
        
        users = User.query.all()
        return render_template('users.html', users=users)

    @app.route('/tournament/<int:tournament_id>')
    @login_required
    def tournament_detail(tournament_id):
        tournament = Tournament.query.get_or_404(tournament_id)
        participants = Participant.query.filter_by(tournament_id=tournament_id).all()
        matches = Match.query.filter_by(tournament_id=tournament_id).all()
        
        # Сортируем участников по имени
        participants.sort(key=lambda x: x.name)
        
        # Создаем турнирную таблицу
        chessboard_data = create_chessboard_data(tournament, participants, matches)
        
        # Создаем детальное расписание
        schedule_display = create_tournament_schedule_display(matches, participants)
        
        # Создаем статистику
        statistics = calculate_statistics(participants, matches, tournament)
        
        # Создаем participants_with_stats для шаблона
        participants_with_stats = []
        for participant in participants:
            participant_stats = statistics.get(participant.id, {
                'games': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'points': 0, 'goal_difference': 0
            })
            participants_with_stats.append({
                'participant': participant,
                'stats': participant_stats,
                'position': 1  # Пока что все на 1 месте
            })
        
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
                'winner_id': match.winner_id,
                'match_date': match.match_date.isoformat() if match.match_date else None,
                'match_time': match.match_time.isoformat() if match.match_time else None,
                'court_number': match.court_number,
                'match_number': match.match_number,
                'status': match.status
            })
        
        return render_template('tournament.html', 
                             tournament=tournament, 
                             participants=participants, 
                             matches=matches,
                             chessboard=chessboard_data,
                             schedule_display=schedule_display,
                             statistics=statistics,
                             participants_with_stats=participants_with_stats,
                             participants_data=participants_data,
                             matches_data=matches_data)

    def create_chessboard_data(tournament, participants, matches):
        """Создает данные для турнирной таблицы"""
        print(f"DEBUG: Создание турнирной таблицы для {len(participants)} участников и {len(matches)} матчей")
        chessboard = create_chessboard(participants, matches)
        print(f"DEBUG: Турнирная таблица создана: {len(chessboard)} строк")
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

def create_chessboard(participants, matches):
    """Создание шахматки для отображения результатов"""
    print(f"DEBUG: create_chessboard вызвана с {len(participants)} участниками и {len(matches)} матчами")
    chessboard = {}
    
    # Сортируем участников по имени для консистентности
    sorted_participants = sorted(participants, key=lambda p: p.name)
    print(f"DEBUG: Отсортированные участники: {[p.name for p in sorted_participants]}")
    
    for p1 in sorted_participants:
        chessboard[p1.id] = {}
        for p2 in sorted_participants:
            if p1.id == p2.id:
                # Диагональ
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
                        # Отображаем время матча и номер площадки в ячейке
                        time_display = ""
                        if match.match_date and match.match_time:
                            time_display = f"{match.match_time.strftime('%H:%M')}"
                        elif match.match_time:
                            time_display = match.match_time.strftime('%H:%M')
                        else:
                            time_display = 'Запланирован'
                        
                        # Добавляем номер площадки
                        court_display = f"Пл.{match.court_number}" if match.court_number else ""
                        full_display = f"{time_display} {court_display}".strip()
                        
                        chessboard[p1.id][p2.id] = {
                            'type': 'upcoming',
                            'value': full_display,
                            'match_id': match.id,
                            'editable': False,
                            'date': match.match_date,
                            'time': match.match_time,
                            'court': match.court_number,
                            'full_info': f"Площадка {match.court_number}, {match.match_date.strftime('%d.%m')} {match.match_time.strftime('%H:%M')}" if match.match_date and match.match_time else f"Площадка {match.court_number}"
                        }
                else:
                    chessboard[p1.id][p2.id] = {'type': 'empty', 'value': ''}
    
    print(f"DEBUG: Турнирная таблица создана: {len(chessboard)} участников")
    for p1_id, row in chessboard.items():
        print(f"DEBUG: Участник {p1_id}: {len(row)} ячеек")
    
    return chessboard

def generate_tournament_schedule(participants, tournament, db, Match):
    """Генерация расписания матчей для турнира с равномерной занятостью игроков"""
    if len(participants) < 2:
        return []
    
    # Удаляем существующие матчи
    existing_matches = Match.query.filter_by(tournament_id=tournament.id).all()
    for match in existing_matches:
        db.session.delete(match)
    db.session.commit()
    
    # Создаем все возможные пары участников
    matches_to_create = []
    for i in range(len(participants)):
        for j in range(i + 1, len(participants)):
            matches_to_create.append((participants[i], participants[j]))
    
    # Сортируем матчи по именам участников для консистентности
    matches_to_create.sort(key=lambda x: (x[0].name, x[1].name))
    
    # Настройки расписания
    start_date = tournament.start_date
    start_time = datetime.strptime("09:00", "%H:%M").time()  # Начало в 9:00
    match_duration = 60  # Длительность матча в минутах
    break_duration = 15  # Перерыв между матчами в минутах
    max_courts = min(tournament.court_count or 4, 4)  # Максимум 4 площадки
    
    # Создаем расписание с равномерной занятостью
    matches = []
    participant_matches = {p.id: [] for p in participants}  # Счетчик матчей для каждого участника
    court_schedule = {i: [] for i in range(1, max_courts + 1)}  # Расписание для каждой площадки
    
    match_number = 1
    current_date = start_date
    current_time = start_time
    
    for participant1, participant2 in matches_to_create:
        # Находим площадку с наименьшей загрузкой
        best_court = min(court_schedule.keys(), key=lambda c: len(court_schedule[c]))
        
        # Находим время, когда оба участника свободны
        best_time = find_best_time_slot(participant1, participant2, participant_matches, 
                                      current_date, current_time, match_duration, break_duration)
        
        if best_time is None:
            # Если не можем найти время в текущий день, переходим на следующий
            current_date = current_date + timedelta(days=1)
            current_time = datetime.strptime("09:00", "%H:%M").time()
            best_time = (current_date, current_time)
        
        match_date, match_time = best_time
        
        # Создаем матч
        match = Match(
            tournament_id=tournament.id,
            participant1_id=participant1.id,
            participant2_id=participant2.id,
            match_date=match_date,
            match_time=match_time,
            court_number=best_court,
            match_number=match_number,
            status='запланирован'
        )
        
        db.session.add(match)
        matches.append(match)
        
        # Обновляем статистику участников
        participant_matches[participant1.id].append((match_date, match_time, match_duration))
        participant_matches[participant2.id].append((match_date, match_time, match_duration))
        
        # Обновляем расписание площадки
        court_schedule[best_court].append((match_date, match_time, match_duration))
        
        # Обновляем время для следующего матча
        current_datetime = datetime.combine(match_date, match_time)
        next_time = current_datetime + timedelta(minutes=match_duration + break_duration)
        current_date = next_time.date()
        current_time = next_time.time()
        
        # Если время больше 18:00, переходим на следующий день
        if current_time > datetime.strptime("18:00", "%H:%M").time():
            current_date = current_date + timedelta(days=1)
            current_time = datetime.strptime("09:00", "%H:%M").time()
        
        match_number += 1
    
    db.session.commit()
    logger.info(f"Создано {len(matches)} матчей для турнира {tournament.name}")
    return matches

def find_best_time_slot(participant1, participant2, participant_matches, 
                       start_date, start_time, match_duration, break_duration):
    """Находит лучшее время для матча, когда оба участника свободны"""
    current_date = start_date
    current_time = start_time
    
    # Проверяем следующие 7 дней
    for day in range(7):
        check_date = current_date + timedelta(days=day)
        check_time = datetime.strptime("09:00", "%H:%M").time() if day > 0 else start_time
        
        # Проверяем время с 9:00 до 18:00
        while check_time <= datetime.strptime("18:00", "%H:%M").time():
            # Проверяем, свободны ли оба участника в это время
            if is_participant_free(participant1.id, participant_matches, check_date, check_time, match_duration) and \
               is_participant_free(participant2.id, participant_matches, check_date, check_time, match_duration):
                return (check_date, check_time)
            
            # Переходим к следующему временному слоту
            current_datetime = datetime.combine(check_date, check_time)
            next_time = current_datetime + timedelta(minutes=match_duration + break_duration)
            check_time = next_time.time()
            
            # Если время больше 18:00, переходим к следующему дню
            if check_time > datetime.strptime("18:00", "%H:%M").time():
                break
    
    return None

def is_participant_free(participant_id, participant_matches, check_date, check_time, match_duration):
    """Проверяет, свободен ли участник в указанное время"""
    participant_schedule = participant_matches.get(participant_id, [])
    
    check_start = datetime.combine(check_date, check_time)
    check_end = check_start + timedelta(minutes=match_duration)
    
    for match_date, match_time, duration in participant_schedule:
        match_start = datetime.combine(match_date, match_time)
        match_end = match_start + timedelta(minutes=duration)
        
        # Проверяем пересечение временных интервалов
        if not (check_end <= match_start or check_start >= match_end):
            return False
    
    return True

def create_tournament_schedule_display(matches, participants):
    """Создает детальное расписание турнира для отображения"""
    if not matches:
        return {}
    
    # Сортируем все матчи по дате и времени для сквозной нумерации
    sorted_matches = sorted(matches, key=lambda m: (m.match_date or datetime.min.date(), m.match_time or datetime.min.time()))
    
    # Создаем сквозную нумерацию
    for i, match in enumerate(sorted_matches, 1):
        match.global_match_number = i
    
    # Группируем матчи по дням
    schedule = {}
    participants_dict = {p.id: p for p in participants}
    
    for match in sorted_matches:
        if not match.match_date:
            continue
            
        date_str = match.match_date.strftime('%Y-%m-%d')
        if date_str not in schedule:
            schedule[date_str] = {
                'date': match.match_date,
                'date_display': match.match_date.strftime('%d.%m.%Y'),
                'matches': []
            }
        
        # Получаем имена участников
        participant1_name = participants_dict.get(match.participant1_id, {}).name if match.participant1_id else f"Участник {match.participant1_id}"
        participant2_name = participants_dict.get(match.participant2_id, {}).name if match.participant2_id else f"Участник {match.participant2_id}"
        
        match_info = {
            'id': match.id,
            'global_number': getattr(match, 'global_match_number', match.match_number or 0),
            'time': match.match_time.strftime('%H:%M') if match.match_time else 'TBD',
            'court': match.court_number or 0,
            'participant1': participant1_name,
            'participant2': participant2_name,
            'status': match.status,
            'score': f"{match.score1}:{match.score2}" if match.score1 is not None and match.score2 is not None else None,
            'match_number': match.match_number
        }
        
        schedule[date_str]['matches'].append(match_info)
    
    # Сортируем матчи по времени в каждом дне
    for date_str in schedule:
        schedule[date_str]['matches'].sort(key=lambda x: x['time'])
    
    return schedule

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
            chessboard = create_chessboard(participants, matches)
            sorted_participants = sorted(participants, key=lambda p: p.name)
            
            f.write("СОЗДАНИЕ ШАХМАТКИ:\n")
            for p1 in sorted_participants:
                f.write(f"\nСтрока для участника {p1.id} ('{p1.name}'):\n")
                for p2 in sorted_participants:
                    cell = chessboard[p1.id][p2.id]
                    f.write(f"  [{p1.id}][{p2.id}] = {cell['type']} ({cell['value']})\n")
            
            f.write(f"\n=== КОНЕЦ ОТЛАДКИ ===\n")
            
        print(f"Данные турнирной таблицы записаны в файл debug_chessboard_{tournament_id}.txt")
        return True
    except Exception as e:
        print(f"Ошибка при записи отладочного файла: {str(e)}")
        return False
