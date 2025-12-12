"""
Модель розыгрыша для бадминтона
Сохраняет детальную информацию о каждом розыгрыше в матче
"""
from datetime import datetime
from . import db

class Rally(db.Model):
    __tablename__ = 'rally'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Связь с матчем
    match_id = db.Column(db.Integer, db.ForeignKey('match.id'), nullable=False)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    
    # Номер сета (1, 2, 3)
    set_number = db.Column(db.Integer, nullable=False)
    
    # Дата и время розыгрыша
    rally_date = db.Column(db.Date, nullable=False, default=lambda: datetime.utcnow().date())
    rally_time = db.Column(db.Time, nullable=False, default=lambda: datetime.utcnow().time())
    rally_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Поле/корт, с которого была подача
    court_number = db.Column(db.Integer, nullable=True)  # номер корта
    
    # Имена игроков
    server_name = db.Column(db.String(100), nullable=False)  # имя подающего
    receiver_name = db.Column(db.String(100), nullable=False)  # имя принимающего
    
    # Результат розыгрыша
    server_won = db.Column(db.Boolean, nullable=False)  # True если выиграл подающий, False если принимающий
    
    # Общий счёт после этого розыгрыша (формат "21:19")
    score = db.Column(db.String(20), nullable=False)  # общий счёт после розыгрыша
    
    # Счётчик смен половин корта для правильного определения направления стрелки
    swap_count = db.Column(db.Integer, nullable=True, default=0)  # счётчик смен половин корта
    
    # Дополнительная информация
    notes = db.Column(db.Text, nullable=True)  # дополнительные заметки о розыгрыше
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Soft-delete поля
    is_removed = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(100), nullable=True)
    
    # Связи
    match = db.relationship('Match', backref='rallies')
    tournament = db.relationship('Tournament', backref='rallies')
    
    def __repr__(self):
        return f'<Rally {self.id}: {self.server_name} vs {self.receiver_name} - Set {self.set_number} at {self.rally_datetime}>'
    
    def to_dict(self):
        """Преобразование в словарь для JSON API"""
        return {
            'id': self.id,
            'match_id': self.match_id,
            'tournament_id': self.tournament_id,
            'set_number': self.set_number,
            'rally_date': self.rally_date.isoformat() if self.rally_date else None,
            'rally_time': self.rally_time.isoformat() if self.rally_time else None,
            'rally_datetime': self.rally_datetime.isoformat() if self.rally_datetime else None,
            'court_number': self.court_number,
            'server_name': self.server_name,
            'receiver_name': self.receiver_name,
            'server_won': self.server_won,
            'score': self.score,
            'swap_count': self.swap_count,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_removed': self.is_removed,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'deleted_by': self.deleted_by
        }

