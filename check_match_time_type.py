"""Проверка типа данных времени в матче"""
from app import app, db
from models.match import Match

with app.app_context():
    match = Match.query.get(44)
    if match:
        print(f"Match ID: {match.id}")
        print(f"match_time: {match.match_time}")
        print(f"match_time type: {type(match.match_time)}")
        print(f"match_date: {match.match_date}")
        print(f"match_date type: {type(match.match_date)}")
        
        if match.match_time:
            print(f"match_time strftime: {match.match_time.strftime('%H:%M')}")
    else:
        print("Match 44 not found")




