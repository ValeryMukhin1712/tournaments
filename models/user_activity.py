"""
Модель для отслеживания активности пользователей
"""
from datetime import datetime, timedelta
from . import db

class UserActivity(db.Model):
    __tablename__ = 'user_activity'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(50), nullable=False)  # 'admin', 'participant', 'viewer'
    user_id = db.Column(db.String(100), nullable=True)  # ID пользователя (может быть email, имя и т.д.)
    session_id = db.Column(db.String(100), nullable=True)  # ID сессии
    ip_address = db.Column(db.String(45), nullable=True)  # IP адрес
    user_agent = db.Column(db.Text, nullable=True)  # User Agent браузера
    page_visited = db.Column(db.String(200), nullable=True)  # Последняя посещенная страница
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Активен ли пользователь
    
    # Новые поля для управления сессиями
    login_token = db.Column(db.String(100), nullable=True)  # Уникальный токен сессии
    email = db.Column(db.String(100), nullable=True)  # Email администратора
    expires_at = db.Column(db.DateTime, nullable=True)  # Время истечения сессии
    is_terminated = db.Column(db.Boolean, default=False, nullable=False)  # Принудительно завершена ли сессия
    terminated_by = db.Column(db.String(100), nullable=True)  # Кто завершил сессию
    terminated_at = db.Column(db.DateTime, nullable=True)  # Когда была завершена
    session_duration = db.Column(db.Integer, nullable=True)  # Продолжительность сессии в секундах
    logout_reason = db.Column(db.String(50), nullable=True)  # Причина завершения
    pages_visited_count = db.Column(db.Integer, default=0, nullable=False)  # Количество посещенных страниц
    last_page = db.Column(db.String(200), nullable=True)  # Последняя посещенная страница
    
    def __repr__(self):
        return f'<UserActivity {self.user_type}:{self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_type': self.user_type,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'page_visited': self.page_visited,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'login_token': self.login_token,
            'email': self.email,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_terminated': self.is_terminated,
            'terminated_by': self.terminated_by,
            'terminated_at': self.terminated_at.isoformat() if self.terminated_at else None,
            'session_duration': self.session_duration,
            'logout_reason': self.logout_reason,
            'pages_visited_count': self.pages_visited_count,
            'last_page': self.last_page
        }
    
    def is_expired(self):
        """Проверяет, истекла ли сессия"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self):
        """Проверяет, валидна ли сессия"""
        return (self.is_active and 
               not self.is_terminated and 
               not self.is_expired())
    
    def calculate_duration(self):
        """Вычисляет продолжительность сессии"""
        if self.terminated_at:
            return int((self.terminated_at - self.created_at).total_seconds())
        elif self.is_active:
            return int((datetime.utcnow() - self.created_at).total_seconds())
        return 0