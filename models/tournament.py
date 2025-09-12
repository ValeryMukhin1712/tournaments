"""
Модель турнира
"""
from datetime import datetime, date

def create_tournament_model(db):
    """Создает модель Tournament с переданным экземпляром db"""
    
    class Tournament(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        sport_type = db.Column(db.String(50), nullable=False)  # теннис, бадминтон, волейбол
        start_date = db.Column(db.Date, nullable=False)
        end_date = db.Column(db.Date, nullable=False)
        max_participants = db.Column(db.Integer, default=32)
        court_count = db.Column(db.Integer, default=3)  # количество площадок
        match_duration = db.Column(db.Integer, default=60)  # продолжительность матча в минутах
        break_duration = db.Column(db.Integer, default=15)  # перерыв между матчами в минутах
        start_time = db.Column(db.Time, default=lambda: datetime.strptime("09:00", "%H:%M").time())  # время начала матчей
        end_time = db.Column(db.Time, default=lambda: datetime.strptime("17:00", "%H:%M").time())  # время окончания матчей
        points_win = db.Column(db.Integer, default=3)  # очки за победу
        points_draw = db.Column(db.Integer, default=1)  # очки за ничью
        points_loss = db.Column(db.Integer, default=0)  # очки за поражение
        points_to_win = db.Column(db.Integer, default=21)  # количество очков для победы в матче
        sets_to_win = db.Column(db.Integer, default=2)  # количество выигранных сетов для победы
        status = db.Column(db.String(20), default='регистрация')  # регистрация, активен, завершен
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<Tournament {self.name}>'
    
    return Tournament
