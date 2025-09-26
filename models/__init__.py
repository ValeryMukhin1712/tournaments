"""
Модели базы данных
"""
from .user import create_user_model
from .tournament import create_tournament_model
from .participant import create_participant_model
from .match import create_match_model
from .notification import create_notification_model
from .match_log import create_match_log_model
from .token import create_token_model
from .waiting_list import create_waiting_list_model

def create_models(db):
    """Создает все модели с переданным экземпляром db"""
    User = create_user_model(db)
    Tournament = create_tournament_model(db)
    Participant = create_participant_model(db)
    Match = create_match_model(db)
    Notification = create_notification_model(db)
    MatchLog = create_match_log_model(db)
    Token = create_token_model(db)
    WaitingList = create_waiting_list_model(db)
    
    return {
        'User': User,
        'Tournament': Tournament,
        'Participant': Participant,
        'Match': Match,
        'Notification': Notification,
        'MatchLog': MatchLog,
        'Token': Token,
        'WaitingList': WaitingList
    }