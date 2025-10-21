"""
Модель журнала изменения счёта в матче
"""
from datetime import datetime
from . import db

class MatchLog(db.Model):
    __tablename__ = 'match_log'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=True)
    set_number = db.Column(db.Integer, nullable=False)  # номер сета (1, 2, 3)
    
    # Временная метка изменения
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Счёт до и после изменения
    previous_score_left = db.Column(db.Integer, nullable=False)
    previous_score_right = db.Column(db.Integer, nullable=False)
    current_score_left = db.Column(db.Integer, nullable=False)
    current_score_right = db.Column(db.Integer, nullable=False)
    
    # Позиция подачи
    serve_position = db.Column(db.String(20), nullable=False)  # bottom_left, top_left, bottom_right, top_right
    
    # Имена игроков
    left_player_name = db.Column(db.String(100), nullable=False)
    right_player_name = db.Column(db.String(100), nullable=False)
    
    # Действие, которое привело к изменению
    action = db.Column(db.String(20), nullable=False)  # +1_left, +1_right, serve_change, team_swap
    
    # Дополнительная информация
    notes = db.Column(db.Text)  # дополнительные заметки
    
    # Связи
    tournament = db.relationship('Tournament', backref='match_logs')
    match = db.relationship('Match', backref='match_logs')
    
    def __repr__(self):
        return f'<MatchLog {self.match_id} Set {self.set_number}: {self.action} at {self.timestamp}>'
    
    def to_dict(self):
        """Преобразование в словарь для JSON API"""
        return {
            'id': self.id,
            'tournament_id': self.tournament_id,
            'match_id': self.match_id,
            'set_number': self.set_number,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'previous_score_left': self.previous_score_left,
            'previous_score_right': self.previous_score_right,
            'current_score_left': self.current_score_left,
            'current_score_right': self.current_score_right,
            'serve_position': self.serve_position,
            'left_player_name': self.left_player_name,
            'right_player_name': self.right_player_name,
            'action': self.action,
            'notes': self.notes
        }