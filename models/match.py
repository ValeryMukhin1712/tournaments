"""
Модель матча
"""
from datetime import datetime, date, time
from . import db

class Match(db.Model):
    __tablename__ = 'match'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=True)  # Теперь nullable для свободных матчей
    participant1_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=True)  # Nullable для свободных матчей
    participant2_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=True)  # Nullable для свободных матчей
    # Поля для свободных матчей (без турнира)
    player1_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)  # Для свободных матчей
    player2_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)  # Для свободных матчей
    player1_name = db.Column(db.String(100), nullable=True)  # Имя игрока/команды 1 (для свободных матчей)
    player2_name = db.Column(db.String(100), nullable=True)  # Имя игрока/команды 2 (для свободных матчей)
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
    winner_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=True)  # Nullable для свободных матчей
    winner_player_id = db.Column(db.Integer, db.ForeignKey('player.id'), nullable=True)  # Для свободных матчей
    match_date = db.Column(db.Date)  # запланированная дата
    match_time = db.Column(db.Time)  # запланированное время начала
    actual_start_time = db.Column(db.DateTime, nullable=True)  # реальное время начала матча
    actual_end_time = db.Column(db.DateTime, nullable=True)  # реальное время окончания матча
    court_number = db.Column(db.Integer)  # номер площадки
    match_number = db.Column(db.Integer)  # последовательный номер игры
    status = db.Column(db.String(20), default='запланирован')  # запланирован, в_процессе, завершен
    # Используем datetime.now вместо datetime.utcnow для учета локального часового пояса
    # Для совместимости с SQLAlchemy используем lambda для callable
    created_at = db.Column(db.DateTime, default=lambda: datetime.now())
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())
    
    # Soft-delete поля
    is_removed = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(100), nullable=True)
    
    # Связи для отображения имен участников
    participant1 = db.relationship('models.participant.Participant', foreign_keys=[participant1_id], backref='matches_as_p1')
    participant2 = db.relationship('models.participant.Participant', foreign_keys=[participant2_id], backref='matches_as_p2')
    # Связи для свободных матчей
    player1 = db.relationship('models.player.Player', foreign_keys=[player1_id], backref='matches_as_p1')
    player2 = db.relationship('models.player.Player', foreign_keys=[player2_id], backref='matches_as_p2')

    def __repr__(self):
        return f'<Match {self.participant1_id} vs {self.participant2_id} in Tournament {self.tournament_id}>'