"""
Модель для хранения токенов доступа
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean

def create_token_model(db):
    """Создает модель Token для базы данных"""
    
    class Token(db.Model):
        __tablename__ = 'tokens'
        
        id = Column(Integer, primary_key=True)
        email = Column(String(255), nullable=False, index=True)
        token = Column(Integer, nullable=False)
        name = Column(String(255), nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
        is_used = Column(Boolean, default=False, nullable=False)
        used_at = Column(DateTime, nullable=True)
        
        def __repr__(self):
            return f'<Token {self.token} for {self.email}>'
    
    return Token
