"""
Система управления сессиями администраторов
"""
import secrets
import logging
from datetime import datetime, timedelta
from flask import request, session
from sqlalchemy import and_, or_

logger = logging.getLogger(__name__)

class SessionManager:
    """Класс для управления сессиями администраторов"""
    
    def __init__(self, db, UserActivity):
        self.db = db
        self.UserActivity = UserActivity
        self.SESSION_TIMEOUT_HOURS = 2  # Время жизни сессии по умолчанию
    
    def generate_session_token(self):
        """Генерирует уникальный токен сессии"""
        return secrets.token_urlsafe(32)
    
    def check_active_session(self, email):
        """
        Проверяет наличие активной сессии для email
        
        Args:
            email (str): Email администратора
            
        Returns:
            tuple: (has_active_session, session_data)
        """
        try:
            active_session = self.UserActivity.query.filter(
                and_(
                    self.UserActivity.email == email,
                    self.UserActivity.is_active == True,
                    self.UserActivity.is_terminated == False,
                    or_(
                        self.UserActivity.expires_at.is_(None),
                        self.UserActivity.expires_at > datetime.utcnow()
                    )
                )
            ).first()
            
            if active_session:
                return True, active_session
            return False, None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке активной сессии для {email}: {e}")
            return False, None
    
    def create_admin_session(self, email, session_data):
        """
        Создает новую сессию администратора
        
        Args:
            email (str): Email администратора
            session_data (dict): Данные сессии
            
        Returns:
            tuple: (success, session_token, error_message)
        """
        try:
            logger.info(f"Начинаем создание сессии для {email}")
            
            # ВРЕМЕННО ОТКЛЮЧЕНО: Проверяем наличие активной сессии
            # has_active, active_session = self.check_active_session(email)
            # logger.info(f"Проверка активной сессии для {email}: has_active={has_active}")
            # 
            # if has_active:
            #     # Завершаем предыдущую сессию
            #     logger.info(f"Завершаем предыдущую сессию для {email}")
            #     self.terminate_session_by_admin(email, 'system', 'duplicate_login')
            
            # Генерируем новый токен
            session_token = self.generate_session_token()
            logger.info(f"Сгенерирован токен сессии: {session_token[:10]}...")
            
            # Вычисляем время истечения
            expires_at = datetime.utcnow() + timedelta(hours=self.SESSION_TIMEOUT_HOURS)
            logger.info(f"Время истечения сессии: {expires_at}")
            
            # Создаем новую запись активности
            logger.info(f"Создаем объект UserActivity для {email}")
            new_activity = self.UserActivity(
                user_type='admin',
                user_id=email,
                session_id=session.get('session_id', 'unknown'),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', ''),
                page_visited=session_data.get('page_visited', '/'),
                last_activity=datetime.utcnow(),
                created_at=datetime.utcnow(),
                is_active=True,
                login_token=session_token,
                email=email,
                expires_at=expires_at,
                is_terminated=False,
                pages_visited_count=1,
                last_page=session_data.get('page_visited', '/'),
                logout_reason=None
            )
            
            logger.info(f"Добавляем объект в сессию базы данных")
            self.db.session.add(new_activity)
            
            logger.info(f"Коммитим изменения в базу данных")
            self.db.session.commit()
            
            logger.info(f"Создана новая сессия для {email}")
            return True, session_token, None
            
        except Exception as e:
            logger.error(f"Ошибка при создании сессии для {email}: {e}")
            self.db.session.rollback()
            return False, None, str(e)
    
    def terminate_session_by_admin(self, email, admin_email, reason='forced'):
        """
        Принудительно завершает сессию администратором
        
        Args:
            email (str): Email пользователя, чью сессию завершают
            admin_email (str): Email администратора, который завершает сессию
            reason (str): Причина завершения
            
        Returns:
            bool: Успешность операции
        """
        try:
            # Находим активные сессии пользователя
            active_sessions = self.UserActivity.query.filter(
                and_(
                    self.UserActivity.email == email,
                    self.UserActivity.is_active == True,
                    self.UserActivity.is_terminated == False
                )
            ).all()
            
            terminated_count = 0
            for session_record in active_sessions:
                session_record.is_active = False
                session_record.is_terminated = True
                session_record.terminated_by = admin_email
                session_record.terminated_at = datetime.utcnow()
                session_record.logout_reason = reason
                session_record.session_duration = session_record.calculate_duration()
                terminated_count += 1
            
            self.db.session.commit()
            
            logger.info(f"Завершено {terminated_count} сессий для {email} администратором {admin_email}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при завершении сессий для {email}: {e}")
            self.db.session.rollback()
            return False
    
    def validate_session(self, session_id, email):
        """
        Проверяет валидность сессии
        
        Args:
            session_id (str): ID сессии
            email (str): Email пользователя
            
        Returns:
            tuple: (is_valid, session_data, error_message)
        """
        try:
            session_record = self.UserActivity.query.filter(
                and_(
                    self.UserActivity.login_token == session_id,
                    self.UserActivity.email == email
                )
            ).first()
            
            if not session_record:
                return False, None, "Сессия не найдена"
            
            if not session_record.is_valid():
                return False, session_record, "Сессия недействительна"
            
            # Обновляем время последней активности
            session_record.last_activity = datetime.utcnow()
            self.db.session.commit()
            
            return True, session_record, None
            
        except Exception as e:
            logger.error(f"Ошибка при проверке сессии {session_id}: {e}")
            return False, None, str(e)
    
    def cleanup_expired_sessions(self):
        """
        Очищает истекшие сессии
        
        Returns:
            int: Количество очищенных сессий
        """
        try:
            now = datetime.utcnow()
            
            # Находим истекшие сессии
            expired_sessions = self.UserActivity.query.filter(
                and_(
                    self.UserActivity.is_active == True,
                    self.UserActivity.expires_at.isnot(None),
                    self.UserActivity.expires_at < now
                )
            ).all()
            
            cleaned_count = 0
            for session_record in expired_sessions:
                session_record.is_active = False
                session_record.logout_reason = 'timeout'
                session_record.session_duration = session_record.calculate_duration()
                cleaned_count += 1
            
            self.db.session.commit()
            
            if cleaned_count > 0:
                logger.info(f"Очищено {cleaned_count} истекших сессий")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке истекших сессий: {e}")
            self.db.session.rollback()
            return 0
    
    def get_all_active_sessions(self):
        """
        Получает все активные сессии
        
        Returns:
            list: Список активных сессий
        """
        try:
            active_sessions = self.UserActivity.query.filter(
                and_(
                    self.UserActivity.is_active == True,
                    self.UserActivity.is_terminated == False,
                    or_(
                        self.UserActivity.expires_at.is_(None),
                        self.UserActivity.expires_at > datetime.utcnow()
                    )
                )
            ).order_by(self.UserActivity.last_activity.desc()).all()
            
            return active_sessions
            
        except Exception as e:
            logger.error(f"Ошибка при получении активных сессий: {e}")
            return []
    
    def get_session_history(self, email=None, date_from=None, date_to=None, limit=100):
        """
        Получает историю сессий
        
        Args:
            email (str): Email пользователя (опционально)
            date_from (datetime): Начальная дата (опционально)
            date_to (datetime): Конечная дата (опционально)
            limit (int): Лимит записей
            
        Returns:
            list: Список сессий из истории
        """
        try:
            query = self.UserActivity.query.filter(
                self.UserActivity.user_type == 'admin'
            )
            
            if email:
                query = query.filter(self.UserActivity.email == email)
            
            if date_from:
                query = query.filter(self.UserActivity.created_at >= date_from)
            
            if date_to:
                query = query.filter(self.UserActivity.created_at <= date_to)
            
            history = query.order_by(
                self.UserActivity.created_at.desc()
            ).limit(limit).all()
            
            return history
            
        except Exception as e:
            logger.error(f"Ошибка при получении истории сессий: {e}")
            return []
    
    def track_page_visit(self, session_token, page_url):
        """
        Отслеживает посещение страницы
        
        Args:
            session_token (str): Токен сессии
            page_url (str): URL страницы
            
        Returns:
            bool: Успешность операции
        """
        try:
            session_record = self.UserActivity.query.filter(
                self.UserActivity.login_token == session_token
            ).first()
            
            if session_record and session_record.is_valid():
                session_record.last_activity = datetime.utcnow()
                session_record.page_visited = page_url
                session_record.last_page = page_url
                session_record.pages_visited_count += 1
                
                self.db.session.commit()
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при отслеживании посещения страницы: {e}")
            return False
    
    def logout_session(self, session_token, reason='normal'):
        """
        Завершает сессию при выходе пользователя
        
        Args:
            session_token (str): Токен сессии
            reason (str): Причина завершения
            
        Returns:
            bool: Успешность операции
        """
        try:
            session_record = self.UserActivity.query.filter(
                self.UserActivity.login_token == session_token
            ).first()
            
            if session_record:
                session_record.is_active = False
                session_record.logout_reason = reason
                session_record.session_duration = session_record.calculate_duration()
                
                self.db.session.commit()
                logger.info(f"Сессия {session_token} завершена с причиной: {reason}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Ошибка при завершении сессии: {e}")
            self.db.session.rollback()
            return False


def create_session_manager(db, UserActivity):
    """Создает экземпляр SessionManager"""
    return SessionManager(db, UserActivity)
