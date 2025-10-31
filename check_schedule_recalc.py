"""
Скрипт для проверки пересчета расписания.
Показывает запланированное и реальное время матчей.
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models.match import Match

def check_schedule():
    """Проверяет расписание матчей и показывает запланированное/реальное время"""
    with app.app_context():
        print("="*80)
        print("ПРОВЕРКА ПЕРЕСЧЕТА РАСПИСАНИЯ")
        print("="*80)
        
        # Получаем все матчи, отсортированные по турниру, площадке и номеру
        matches = Match.query.order_by(
            Match.tournament_id,
            Match.court_number,
            Match.match_number
        ).all()
        
        if not matches:
            print("Нет матчей в базе данных")
            return
        
        current_tournament = None
        current_court = None
        
        for match in matches:
            # Разделитель для нового турнира
            if match.tournament_id != current_tournament:
                current_tournament = match.tournament_id
                current_court = None
                print(f"\n{'='*80}")
                print(f"ТУРНИР ID: {match.tournament_id}")
                print(f"{'='*80}\n")
            
            # Разделитель для новой площадки
            if match.court_number != current_court:
                current_court = match.court_number
                print(f"\n{'─'*80}")
                print(f"ПЛОЩАДКА {match.court_number}")
                print(f"{'─'*80}\n")
            
            # Формируем строку с информацией о матче
            date_str = match.match_date.strftime('%d.%m.%Y') if match.match_date else 'Дата не указана'
            time_str = match.match_time.strftime('%H:%M') if match.match_time else 'Время не указано'
            
            actual_start_str = ''
            if match.actual_start_time:
                actual_start_str = f" | Реальное начало: {match.actual_start_time.strftime('%d.%m.%Y %H:%M:%S')}"
            
            actual_end_str = ''
            if match.actual_end_time:
                actual_end_str = f" | Реальное окончание: {match.actual_end_time.strftime('%d.%m.%Y %H:%M:%S')}"
            
            status_icon = {
                'запланирован': '📅',
                'в_процессе': '▶️',
                'играют': '▶️',
                'завершен': '✅'
            }.get(match.status, '❓')
            
            print(f"Матч #{match.match_number} (ID: {match.id})")
            print(f"  {status_icon} Статус: {match.status}")
            print(f"  📆 Запланировано: {date_str} {time_str}{actual_start_str}{actual_end_str}")
            
            if match.status == 'завершен' and match.actual_end_time:
                # Показываем информацию о пересчете
                print(f"  ✓ Матч завершен, время фиксировано: {match.actual_end_time.strftime('%H:%M:%S')}")
            
            print()

if __name__ == '__main__':
    check_schedule()


