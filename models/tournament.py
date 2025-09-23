"""
Модель турнира
"""
from datetime import datetime, date

def create_tournament_model(db):
    """Создает модель Tournament с переданным экземпляром db"""
    
    class Tournament(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(100), nullable=False)
        description = db.Column(db.Text, nullable=True)  # описание турнира
        sport_type = db.Column(db.String(50), nullable=False, default='пинг-понг')  # пинг-понг, бадминтон, волейбол
        start_date = db.Column(db.Date, nullable=True)
        end_date = db.Column(db.Date, nullable=True)
        max_participants = db.Column(db.Integer, default=32)
        court_count = db.Column(db.Integer, default=4)  # количество площадок
        match_duration = db.Column(db.Integer, default=15)  # продолжительность матча в минутах (пинг-понг)
        break_duration = db.Column(db.Integer, default=2)  # перерыв между матчами в минутах (пинг-понг)
        start_time = db.Column(db.Time, nullable=True)  # время начала матчей
        end_time = db.Column(db.Time, nullable=True)  # время окончания матчей
        points_win = db.Column(db.Integer, default=1)  # очки за победу
        points_draw = db.Column(db.Integer, default=1)  # очки за ничью
        points_loss = db.Column(db.Integer, default=0)  # очки за поражение
        points_to_win = db.Column(db.Integer, default=11)  # количество очков для победы в матче (пинг-понг)
        sets_to_win = db.Column(db.Integer, default=2)  # количество выигранных сетов для победы (пинг-понг)
        status = db.Column(db.String(20), default='регистрация')  # регистрация, активен, завершен
        created_at = db.Column(db.DateTime, default=datetime.utcnow)
        admin_id = db.Column(db.Integer, nullable=True)  # ID администратора турнира

        def __repr__(self):
            return f'<Tournament {self.name}>'
    
    return Tournament
