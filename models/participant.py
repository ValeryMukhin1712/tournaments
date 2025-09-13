"""
Модель участника турнира
"""
from datetime import datetime

def create_participant_model(db):
    """Создает модель Participant с переданным экземпляром db"""
    
    class Participant(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
        name = db.Column(db.String(100), nullable=False)
        is_team = db.Column(db.Boolean, default=False)
        points = db.Column(db.Integer, default=0)
        registered_at = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<Participant {self.name}>'
    
    return Participant
