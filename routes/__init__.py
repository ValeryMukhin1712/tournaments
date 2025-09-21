"""
Маршруты приложения
"""
from .main import create_main_routes
from .auth import create_auth_routes
from .api import create_api_routes

def register_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, TournamentAdmin):
    """Регистрирует все маршруты приложения"""
    create_main_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, TournamentAdmin)
    create_auth_routes(app, db, User)
    create_api_routes(app, db, User, Tournament, Participant, Match, Notification, MatchLog, TournamentAdmin)
