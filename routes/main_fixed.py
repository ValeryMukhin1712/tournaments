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
            start_date = request.form.get('start_date')
            end_date = request.form.get('end_date')
            max_participants = int(request.form.get('max_participants', 32))
            court_count = int(request.form.get('court_count', 4))
            match_duration = int(request.form.get('match_duration', 60))
            break_duration = int(request.form.get('break_duration', 15))
            sets_to_win = int(request.form.get('sets_to_win', 2))
            points_to_win = int(request.form.get('points_to_win', 21))
            points_win = int(request.form.get('points_win', 3))
            points_draw = int(request.form.get('points_draw', 1))
            points_loss = int(request.form.get('points_loss', 0))
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            
            if not name:
                flash('Пожалуйста, введите название турнира', 'error')
                return render_template('admin_create_tournament.html', admin=admin)
            
            try:
                # Создаем турнир
                tournament = Tournament(
                    name=name,
                    description=description or '',
                    start_date=datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None,
                    end_date=datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None,
                    max_participants=max_participants or 32,
                    court_count=court_count or 4,
                    match_duration=match_duration or 60,
                    break_duration=break_duration or 15,
                    sets_to_win=sets_to_win or 2,
                    points_to_win=points_to_win or 21,
                    points_win=points_win or 3,
                    points_draw=points_draw or 1,
                    points_loss=points_loss or 0,
                    start_time=start_time or '09:00',
                    end_time=end_time or '18:00',
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

