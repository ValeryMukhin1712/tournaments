"""
Модель лога матча
"""
from datetime import datetime

def create_match_log_model(db):
    """Создает модель MatchLog с переданным экземпляром db"""
    
    class MatchLog(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        action = db.Column(db.String(50), nullable=False)  # создан, изменен, удален
        old_score1 = db.Column(db.Integer)
        old_score2 = db.Column(db.Integer)
        new_score1 = db.Column(db.Integer)
        new_score2 = db.Column(db.Integer)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<MatchLog {self.id} for Match {self.match_id}>'
    
    return MatchLog
