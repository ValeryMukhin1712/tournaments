"""
Модель для админов турниров
"""
from datetime import datetime

def create_tournament_admin_model(db):
    """Создает модель TournamentAdmin с переданным экземпляром db"""
    
    class TournamentAdmin(db.Model):
        """Админ турнира"""
        __tablename__ = 'tournament_admin'
        
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        email = db.Column(db.String(120), nullable=False, unique=True)
        token = db.Column(db.String(50), nullable=False, unique=True)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        is_active = db.Column(db.Boolean, default=True)
        
        # Связь с турнирами
        tournaments = db.relationship('Tournament', backref='admin', lazy=True)
        
        def __repr__(self):
            return f'<TournamentAdmin {self.name} ({self.email})>'
        
        def to_dict(self):
            return {
                'id': self.id,
                'name': self.name,
                'email': self.email,
                'token': self.token,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'is_active': self.is_active
            }
    
    return TournamentAdmin
