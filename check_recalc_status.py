"""
Быстрая проверка статуса пересчета времени матчей.
Показывает, были ли вызваны функции пересчета.
"""

from app import app, db
from models.match import Match
from models.tournament import Tournament
from datetime import datetime, timedelta

def check_recalc_status(tournament_id=17):
    """Проверяет, был ли выполнен пересчет для завершенных матчей"""
    
    with app.app_context():
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            print(f"❌ Турнир с ID {tournament_id} не найден")
            return
        
        print(f"\n📋 Турнир: {tournament.name} (ID: {tournament_id})")
        print(f"Длительность матча: {tournament.match_duration or 15} мин")
        print(f"Перерыв между матчами: {tournament.break_duration or 2} мин")
        print("=" * 80)
        
        # Получаем все завершенные матчи
        completed_matches = Match.query.filter_by(
            tournament_id=tournament_id,
            status='завершен'
        ).order_by(Match.court_number.asc(), Match.match_number.asc()).all()
        
        if not completed_matches:
            print("❌ Нет завершенных матчей в турнире")
            return
        
        print(f"\n✅ Найдено завершенных матчей: {len(completed_matches)}\n")
        
        for completed_match in completed_matches:
            print(f"\n🏟️  Матч #{completed_match.match_number} (ID: {completed_match.id})")
            print(f"   Площадка: {completed_match.court_number}")
            print(f"   Статус: {completed_match.status}")
            
            if completed_match.actual_end_time:
                print(f"   Реальное время окончания: {completed_match.actual_end_time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Прошло времени с окончания: {(datetime.now() - completed_match.actual_end_time).total_seconds() / 60:.1f} мин")
            else:
                print(f"   ⚠️  Реальное время окончания НЕ установлено!")
                if completed_match.updated_at:
                    print(f"   Используем updated_at: {completed_match.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Ищем следующий матч на той же площадке
            next_match = Match.query.filter(
                Match.tournament_id == tournament_id,
                Match.court_number == completed_match.court_number,
                Match.id != completed_match.id,
                Match.status != 'завершен',
                Match.match_number > completed_match.match_number
            ).order_by(Match.match_number.asc()).first()
            
            if not next_match:
                # Пробуем найти любой незавершенный матч на площадке
                next_match = Match.query.filter(
                    Match.tournament_id == tournament_id,
                    Match.court_number == completed_match.court_number,
                    Match.id != completed_match.id,
                    Match.status != 'завершен'
                ).order_by(Match.id.asc()).first()
            
            if next_match:
                print(f"\n   ⬇️  Следующий матч: #{next_match.match_number} (ID: {next_match.id})")
                print(f"      Запланировано: {next_match.match_date} {next_match.match_time}")
                
                # Рассчитываем ожидаемое время начала
                if completed_match.actual_end_time:
                    expected_start = completed_match.actual_end_time + timedelta(minutes=tournament.break_duration or 2)
                elif completed_match.updated_at:
                    expected_start = completed_match.updated_at + timedelta(minutes=tournament.break_duration or 2)
                else:
                    expected_start = None
                
                if expected_start:
                    expected_time_str = expected_start.strftime('%H:%M')
                    expected_date_str = expected_start.strftime('%Y-%m-%d')
                    
                    if next_match.match_time:
                        current_time_str = next_match.match_time.strftime('%H:%M')
                        current_date_str = str(next_match.match_date) if next_match.match_date else "Не указано"
                        
                        expected_datetime = datetime.combine(expected_start.date(), expected_start.time())
                        if next_match.match_date and next_match.match_time:
                            current_datetime = datetime.combine(next_match.match_date, next_match.match_time)
                            time_diff = (current_datetime - expected_datetime).total_seconds() / 60
                            
                            if abs(time_diff) < 1:
                                print(f"      ✅ Время соответствует пересчету: {expected_time_str}")
                            else:
                                print(f"      ❌ Время НЕ соответствует пересчету!")
                                print(f"         Ожидается: {expected_date_str} {expected_time_str}")
                                print(f"         Текущее:   {current_date_str} {current_time_str}")
                                print(f"         Разница:   {time_diff:.1f} мин")
                        else:
                            print(f"      ⚠️  Дата/время следующего матча не полностью установлены")
                            print(f"         Ожидается: {expected_date_str} {expected_time_str}")
                    else:
                        print(f"      ⚠️  Время следующего матча не указано")
                        print(f"         Ожидается: {expected_start.strftime('%Y-%m-%d %H:%M')}")
            else:
                print(f"   ℹ️  Нет следующих матчей на площадке {completed_match.court_number}")
        
        print("\n" + "=" * 80)
        print("💡 Если время следующего матча не соответствует ожидаемому,")
        print("   значит функция пересчета не вызвалась или не нашла следующий матч.")
        print("=" * 80)

if __name__ == "__main__":
    check_recalc_status(17)

