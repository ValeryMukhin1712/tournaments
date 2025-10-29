"""
Модель листа ожидания для турниров
"""
from datetime import datetime
from . import db

class WaitingList(db.Model):
    __tablename__ = 'waiting_list'
    __table_args__ = {'extend_existing': True}
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    skill_level = db.Column(db.String(50), nullable=False)  # "хочу попробовать", "не распробовал", "впал в зависимость"
    telegram = db.Column(db.String(100), nullable=True)  # Chat ID игрока (заполняется автоматически через QR-код)
    telegram_token = db.Column(db.String(100), nullable=True, unique=True)  # Уникальный токен для привязки через QR-код
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ожидает')  # "ожидает", "принят", "отклонен"

    def __repr__(self):
        return f'<WaitingList {self.name} - {self.skill_level}>'