"""
Модель матча
"""
from datetime import datetime, date, time
from . import db

class Match(db.Model):
    __tablename__ = 'match'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    participant1_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    participant2_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    score1 = db.Column(db.Integer)
    score2 = db.Column(db.Integer)
    score = db.Column(db.String(20))  # результат матча в формате "2:1"
    sets_won_1 = db.Column(db.Integer, default=0)  # количество выигранных сетов участником 1
    sets_won_2 = db.Column(db.Integer, default=0)  # количество выигранных сетов участником 2
    # Данные сетов
    set1_score1 = db.Column(db.Integer)  # счет первого сета участника 1
    set1_score2 = db.Column(db.Integer)  # счет первого сета участника 2
    set2_score1 = db.Column(db.Integer)  # счет второго сета участника 1
    set2_score2 = db.Column(db.Integer)  # счет второго сета участника 2
    set3_score1 = db.Column(db.Integer)  # счет третьего сета участника 1
    set3_score2 = db.Column(db.Integer)  # счет третьего сета участника 2
    winner_id = db.Column(db.Integer, db.ForeignKey('participant.id'))
    match_date = db.Column(db.Date)
    match_time = db.Column(db.Time)
    court_number = db.Column(db.Integer)  # номер площадки
    match_number = db.Column(db.Integer)  # последовательный номер игры
    status = db.Column(db.String(20), default='запланирован')  # запланирован, в_процессе, завершен
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи для отображения имен участников
    participant1 = db.relationship('models.participant.Participant', foreign_keys=[participant1_id], backref='matches_as_p1')
    participant2 = db.relationship('models.participant.Participant', foreign_keys=[participant2_id], backref='matches_as_p2')

    def __repr__(self):
        return f'<Match {self.participant1_id} vs {self.participant2_id} in Tournament {self.tournament_id}>'