"""
Модель для хранения паролей доступа
"""
from datetime import datetime
from . import db

class Token(db.Model):
    __tablename__ = 'tokens'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False, index=True)
    token = db.Column(db.Integer, nullable=False, unique=True, index=True)
    name = db.Column(db.String(255), nullable=False)
    telegram = db.Column(db.String(100), nullable=True)  # Chat ID или @username для уведомлений в TG
    telegram_chat_id = db.Column(db.String(32), nullable=True)  # Числовой chat_id после автопривязки через deep link
    telegram_link_token = db.Column(db.String(128), nullable=True, index=True)  # Временный токен для deep link
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    is_used = db.Column(db.Boolean, default=False, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    email_sent = db.Column(db.Boolean, default=False, nullable=False)
    email_sent_at = db.Column(db.DateTime, nullable=True)
    email_status = db.Column(db.String(50), default='pending', nullable=False)

    def __repr__(self):
        return f'<Token {self.token} for {self.email}>'