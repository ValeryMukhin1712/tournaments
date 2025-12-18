"""
Модель участника турнира
"""
from datetime import datetime
from . import db

class Participant(db.Model):
    __tablename__ = 'participant'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    is_team = db.Column(db.Boolean, default=False)
    points = db.Column(db.Integer, default=0)
    telegram = db.Column(db.String(100), nullable=True)  # Telegram контакт игрока (необязательно)
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Soft-delete поля
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    deleted_by = db.Column(db.String(100), nullable=True)

    def __repr__(self):
        return f'<Participant {self.name}>'
