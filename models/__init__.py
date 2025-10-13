"""
Модели базы данных
"""
from flask_sqlalchemy import SQLAlchemy

# Глобальный экземпляр db для моделей
db = SQLAlchemy()

# Импортируем модели напрямую
from .user import User
from .tournament import Tournament
from .participant import Participant
from .match import Match
from .notification import Notification
from .match_log import MatchLog
from .token import Token
from .waiting_list import WaitingList
from .settings import Settings
from .player import Player
from .user_activity import UserActivity

def create_models(db_instance):
    """Возвращает словарь с моделями (для обратной совместимости)"""
    return {
        'User': User,
        'Tournament': Tournament,
        'Participant': Participant,
        'Match': Match,
        'Notification': Notification,
        'MatchLog': MatchLog,
        'Token': Token,
        'WaitingList': WaitingList,
        'Settings': Settings,
        'Player': Player,
        'UserActivity': UserActivity
    }