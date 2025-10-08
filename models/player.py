"""
Модель игрока
"""
from datetime import datetime

def create_player_model(db):
    """Создает модель Player с переданным экземпляром db"""
    
    class Player(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False, unique=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        last_used_at = db.Column(db.DateTime, default=datetime.utcnow)
        
        def __repr__(self):
            return f'<Player {self.name}>'
    
    return Player


