"""
Модель пользователя
"""
from flask_login import UserMixin
from datetime import datetime

def create_user_model(db):
    """Создает модель User с переданным экземпляром db"""
    
    class User(UserMixin, db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(80), unique=True, nullable=False)
        password_hash = db.Column(db.String(120), nullable=False)
        role = db.Column(db.String(20), default='участник')  # участник, доверенный_участник, администратор
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<User {self.username}>'
    
    return User
