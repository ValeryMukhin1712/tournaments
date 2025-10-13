"""
Middleware для проверки сессий и отслеживания активности
"""
import logging
from functools import wraps
from flask import session, request, redirect, url_for, jsonify
from datetime import datetime

logger = logging.getLogger(__name__)

def require_valid_session(f):
    """
    Декоратор для проверки валидности сессии администратора
    
    Args:
        f: Функция для обертывания
        
    Returns:
        Обернутая функция
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from utils.session_manager import create_session_manager
        from models import create_models
        
        # Получаем модели - используем глобальный db из app context
        from app import db
        models = create_models(db)
        UserActivity = models['UserActivity']
        
        # Создаем менеджер сессий
        session_manager = create_session_manager(None, UserActivity)  # db будет получен из app context
        
        # Получаем данные сессии
        session_token = session.get('session_token')
        admin_email = session.get('admin_email')
        
        if not session_token or not admin_email:
            logger.warning(f"Попытка доступа без токена сессии: {request.endpoint}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Сессия не найдена. Войдите в систему.',
                    'redirect_url': url_for('admin_tournament')
                }), 401
            return redirect(url_for('admin_tournament'))
        
        # Проверяем валидность сессии
        is_valid, session_data, error = session_manager.validate_session(session_token, admin_email)
        
        if not is_valid:
            logger.warning(f"Недействительная сессия {session_token} для {admin_email}: {error}")
            
            # Очищаем сессию
            session.pop('admin_id', None)
            session.pop('admin_name', None)
            session.pop('admin_email', None)
            session.pop('is_system_admin', None)
            session.pop('session_token', None)
            
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Сессия истекла или была завершена. Войдите в систему.',
                    'redirect_url': url_for('admin_tournament')
                }), 401
            
            return redirect(url_for('admin_tournament'))
        
        # Отслеживаем посещение страницы
        try:
            session_manager.track_page_visit(session_token, request.endpoint)
        except Exception as e:
            logger.error(f"Ошибка при отслеживании посещения страницы: {e}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def track_user_activity(f):
    """
    Декоратор для отслеживания активности пользователей
    
    Args:
        f: Функция для обертывания
        
    Returns:
        Обернутая функция
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from utils.user_activity import track_user_activity
        from models import create_models
        
        # Получаем модели - используем глобальный db из app context
        from app import db
        models = create_models(db)
        UserActivity = models['UserActivity']
        
        # Определяем тип пользователя
        user_type = 'viewer'
        user_id = None
        
        if session.get('admin_id'):
            user_type = 'admin'
            user_id = session.get('admin_email', 'unknown')
        elif session.get('participant_id'):
            user_type = 'participant'
            user_id = session.get('participant_name', 'unknown')
        
        # Отслеживаем активность
        try:
            track_user_activity(
                db=None,  # db будет получен из app context
                UserActivity=UserActivity,
                user_type=user_type,
                user_id=user_id,
                page_visited=request.endpoint
            )
        except Exception as e:
            logger.error(f"Ошибка при отслеживании активности: {e}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def cleanup_expired_sessions(f):
    """
    Декоратор для периодической очистки истекших сессий
    
    Args:
        f: Функция для обертывания
        
    Returns:
        Обернутая функция
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from utils.session_manager import create_session_manager
        from models import create_models
        
        # Получаем модели - используем глобальный db из app context
        from app import db
        models = create_models(db)
        UserActivity = models['UserActivity']
        
        # Создаем менеджер сессий
        session_manager = create_session_manager(None, UserActivity)
        
        # Очищаем истекшие сессии (выполняем не чаще чем раз в 5 минут)
        last_cleanup = session.get('last_cleanup')
        now = datetime.utcnow()
        
        if not last_cleanup or (now - last_cleanup).total_seconds() > 300:  # 5 минут
            try:
                cleaned_count = session_manager.cleanup_expired_sessions()
                if cleaned_count > 0:
                    logger.info(f"Очищено {cleaned_count} истекших сессий")
                session['last_cleanup'] = now
            except Exception as e:
                logger.error(f"Ошибка при очистке истекших сессий: {e}")
        
        return f(*args, **kwargs)
    
    return decorated_function

def require_system_admin(f):
    """
    Декоратор для проверки прав системного администратора
    
    Args:
        f: Функция для обертывания
        
    Returns:
        Обернутая функция
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_system_admin'):
            logger.warning(f"Попытка доступа к системной функции без прав: {request.endpoint}")
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Недостаточно прав доступа'
                }), 403
            flash('Недостаточно прав доступа', 'error')
            return redirect(url_for('admin_tournament'))
        
        return f(*args, **kwargs)
    
    return decorated_function

def log_admin_actions(f):
    """
    Декоратор для логирования действий администратора
    
    Args:
        f: Функция для обертывания
        
    Returns:
        Обернутая функция
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin_email = session.get('admin_email', 'unknown')
        endpoint = request.endpoint
        method = request.method
        
        logger.info(f"Админ {admin_email} выполняет действие: {method} {endpoint}")
        
        try:
            result = f(*args, **kwargs)
            logger.info(f"Действие {endpoint} выполнено успешно для {admin_email}")
            return result
        except Exception as e:
            logger.error(f"Ошибка при выполнении {endpoint} для {admin_email}: {e}")
            raise
    
    return decorated_function
