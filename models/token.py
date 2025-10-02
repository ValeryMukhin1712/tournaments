"""
Модель для хранения паролей доступа
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean

def create_token_model(db):
    """Создает модель Token для базы данных (пароли доступа)"""
    
    class Token(db.Model):
        __tablename__ = 'tokens'
        
        id = Column(Integer, primary_key=True)
        email = Column(String(255), nullable=False, index=True)
        token = Column(Integer, nullable=False, unique=True, index=True)
        name = Column(String(255), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        is_used = Column(Boolean, default=False, nullable=False)
        used_at = Column(DateTime, nullable=True)
        email_sent = Column(Boolean, default=False, nullable=False)
        email_sent_at = Column(DateTime, nullable=True)
        email_status = Column(String(50), default='pending', nullable=False)  # pending, sent, failed, manual
        
        def __repr__(self):
            return f'<Password {self.token} for {self.email}>'
    
    return Token
