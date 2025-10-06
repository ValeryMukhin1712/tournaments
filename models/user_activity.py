"""
Модель для отслеживания активности пользователей
"""
from datetime import datetime

def create_user_activity_model(db):
    """Создает модель UserActivity для отслеживания активности пользователей"""
    
    class UserActivity(db.Model):
        __tablename__ = 'user_activity'
        
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
                'is_active': self.is_active
            }
    
    return UserActivity
