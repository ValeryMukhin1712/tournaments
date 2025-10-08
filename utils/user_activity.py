"""
Утилиты для отслеживания активности пользователей
"""
from datetime import datetime, timedelta
from flask import request, session

def track_user_activity(db, UserActivity, user_type, user_id=None, page_visited=None):
    """
    Отслеживает активность пользователя
    
    Args:
        db: Экземпляр базы данных
        UserActivity: Модель UserActivity
        user_type: Тип пользователя ('admin', 'participant', 'viewer')
        user_id: ID пользователя (email, имя и т.д.)
        page_visited: Последняя посещенная страница
    """
    try:
        # Получаем информацию о сессии
        session_id = session.get('session_id', 'anonymous')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        # Ищем существующую активность для этого пользователя
        existing_activity = UserActivity.query.filter_by(
            user_type=user_type,
            user_id=user_id,
            session_id=session_id
        ).first()
        
        if existing_activity:
            # Обновляем существующую запись
            existing_activity.last_activity = datetime.utcnow()
            existing_activity.page_visited = page_visited or request.endpoint
            existing_activity.ip_address = ip_address
            existing_activity.user_agent = user_agent
            existing_activity.is_active = True
        else:
            # Создаем новую запись
            new_activity = UserActivity(
                user_type=user_type,
                user_id=user_id,
                session_id=session_id,
                ip_address=ip_address,
                user_agent=user_agent,
                page_visited=page_visited or request.endpoint,
                last_activity=datetime.utcnow(),
                is_active=True
            )
            db.session.add(new_activity)
        
        db.session.commit()
        
    except Exception as e:
        print(f"Ошибка при отслеживании активности: {e}")
        db.session.rollback()

def get_active_users_count(db, UserActivity, minutes_threshold=30):
    """
    Получает количество активных пользователей по типам
    
    Args:
        db: Экземпляр базы данных
        UserActivity: Модель UserActivity
        minutes_threshold: Порог активности в минутах (по умолчанию 30)
    
    Returns:
        dict: Словарь с количеством активных пользователей по типам
    """
    try:
        # Время активности
        active_time = datetime.utcnow() - timedelta(minutes=minutes_threshold)
        
        # Получаем уникальных активных пользователей по типам
        active_admins = db.session.query(UserActivity.user_id).filter(
            UserActivity.user_type == 'admin',
            UserActivity.last_activity >= active_time,
            UserActivity.is_active == True
        ).distinct().count()
        
        active_participants = db.session.query(UserActivity.user_id).filter(
            UserActivity.user_type == 'participant',
            UserActivity.last_activity >= active_time,
            UserActivity.is_active == True
        ).distinct().count()
        
        active_viewers = db.session.query(UserActivity.user_id).filter(
            UserActivity.user_type == 'viewer',
            UserActivity.last_activity >= active_time,
            UserActivity.is_active == True
        ).distinct().count()
        
        return {
            'active_admins': active_admins,
            'active_participants': active_participants,
            'active_viewers': active_viewers,
            'total_active': active_admins + active_participants + active_viewers
        }
        
    except Exception as e:
        print(f"Ошибка при получении статистики активности: {e}")
        return {
            'active_admins': 0,
            'active_participants': 0,
            'active_viewers': 0,
            'total_active': 0
        }

def cleanup_old_activity(db, UserActivity, days_threshold=7):
    """
    Очищает старые записи активности
    
    Args:
        db: Экземпляр базы данных
        UserActivity: Модель UserActivity
        days_threshold: Порог в днях для удаления старых записей
    """
    try:
        cutoff_time = datetime.utcnow() - timedelta(days=days_threshold)
        
        # Удаляем старые записи
        deleted_count = UserActivity.query.filter(
            UserActivity.last_activity < cutoff_time
        ).delete()
        
        db.session.commit()
        
        print(f"Удалено {deleted_count} старых записей активности")
        return deleted_count
        
    except Exception as e:
        print(f"Ошибка при очистке старых записей: {e}")
        db.session.rollback()
        return 0

def mark_user_inactive(db, UserActivity, user_type, user_id, session_id=None):
    """
    Помечает пользователя как неактивного
    
    Args:
        db: Экземпляр базы данных
        UserActivity: Модель UserActivity
        user_type: Тип пользователя
        user_id: ID пользователя
        session_id: ID сессии (опционально)
    """
    try:
        query = UserActivity.query.filter_by(
            user_type=user_type,
            user_id=user_id
        )
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        activities = query.all()
        
        for activity in activities:
            activity.is_active = False
        
        db.session.commit()
        
    except Exception as e:
        print(f"Ошибка при пометке пользователя как неактивного: {e}")
        db.session.rollback()

