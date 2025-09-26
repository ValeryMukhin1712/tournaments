"""
Модель листа ожидания для турниров
"""
from datetime import datetime

def create_waiting_list_model(db):
    """Создает модель WaitingList с переданным экземпляром db"""
    
    class WaitingList(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'), nullable=False)
        name = db.Column(db.String(100), nullable=False)
        skill_level = db.Column(db.String(50), nullable=False)  # "хочу попробовать", "не распробовал", "впал в зависимость"
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        status = db.Column(db.String(20), default='ожидает')  # "ожидает", "принят", "отклонен"

        def __repr__(self):
            return f'<WaitingList {self.name} - {self.skill_level}>'
    
    return WaitingList
