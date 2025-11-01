"""
Скрипт для проверки функционала пересчёта времени начала матчей.
Показывает информацию о матчах на площадке до и после пересчёта.
"""

from app import app, db
from models.match import Match
from models.tournament import Tournament
from datetime import datetime, timedelta

def test_schedule_recalculation():
    """Проверяет пересчёт времени начала матчей"""
    
    with app.app_context():
        # Запрашиваем ID турнира
        tournament_id = input("Введите ID турнира для проверки (например, 17): ").strip()
        
        try:
            tournament_id = int(tournament_id)
        except ValueError:
            print("❌ Неверный ID турнира")
            return
        
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            print(f"❌ Турнир с ID {tournament_id} не найден")
            return
        
        print(f"\n📋 Турнир: {tournament.name} (ID: {tournament_id})")
        print(f"Длительность матча: {tournament.match_duration or 15} минут")
        print(f"Перерыв между матчами: {tournament.break_duration or 2} минут")
        print("-" * 80)
        
        # Получаем все матчи турнира, сгруппированные по площадкам
        matches = Match.query.filter_by(tournament_id=tournament_id).order_by(
            Match.court_number.asc(),
            Match.match_number.asc()
        ).all()
        
        if not matches:
            print("❌ Матчи не найдены")
            return
        
        # Группируем по площадкам
        courts = {}
        for match in matches:
            court = match.court_number or "Без площадки"
            if court not in courts:
                courts[court] = []
            courts[court].append(match)
        
        print("\n📊 Текущее расписание матчей:\n")
        
        for court, court_matches in sorted(courts.items()):
            print(f"\n🏟️  Площадка {court}:")
            print("-" * 80)
            
            for i, match in enumerate(court_matches):
                status_icon = "✅" if match.status == "завершен" else "⏳" if match.status == "в_процессе" else "📅"
                
                match_time_str = f"{match.match_date or 'Не указано'} {match.match_time or 'Не указано'}"
                
                if match.actual_start_time:
                    actual_start = match.actual_start_time.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    actual_start = "—"
                
                if match.actual_end_time:
                    actual_end = match.actual_end_time.strftime("%Y-%m-%d %H:%M:%S")
                    time_since_end = (datetime.utcnow() - match.actual_end_time).total_seconds() / 60
                    time_info = f" (завершён {time_since_end:.1f} мин назад)"
                else:
                    actual_end = "—"
                    time_info = ""
                
                print(f"  {status_icon} Матч #{match.match_number} (ID: {match.id})")
                print(f"     Участники: {match.participant1 or '?'} vs {match.participant2 or '?'}")
                print(f"     Запланировано: {match_time_str}")
                print(f"     Статус: {match.status}")
                
                if match.actual_start_time or match.actual_end_time:
                    print(f"     Реальное начало: {actual_start}")
                    print(f"     Реальное окончание: {actual_end}{time_info}")
                
                # Показываем следующий матч на этой площадке
                if i < len(court_matches) - 1:
                    next_match = court_matches[i + 1]
                    print(f"     ⬇️ Следующий матч #{next_match.match_number} запланирован: {next_match.match_date or 'Не указано'} {next_match.match_time or 'Не указано'}")
                    
                    # Если текущий матч завершён, показываем расчёт для следующего
                    if match.status == "завершен" and match.actual_end_time:
                        break_duration = tournament.break_duration or 2
                        expected_next_start = match.actual_end_time + timedelta(minutes=break_duration)
                        
                        if next_match.match_time:
                            next_planned = datetime.combine(
                                next_match.match_date or datetime.utcnow().date(),
                                next_match.match_time
                            )
                            
                            time_diff = (next_planned - expected_next_start).total_seconds() / 60
                            
                            if abs(time_diff) < 1:  # Разница менее 1 минуты
                                print(f"     ✅ Время следующего матча соответствует расчёту ({expected_next_start.strftime('%H:%M')})")
                            else:
                                print(f"     ⚠️  Время следующего матча отличается на {time_diff:.1f} мин")
                                print(f"        Ожидается: {expected_next_start.strftime('%Y-%m-%d %H:%M')}")
                                print(f"        Запланировано: {next_planned.strftime('%Y-%m-%d %H:%M')}")
                
                print()
        
        print("\n" + "=" * 80)
        print("💡 Для проверки пересчёта:")
        print("   1. Завершите один из матчей через веб-интерфейс")
        print("   2. Запустите этот скрипт снова")
        print("   3. Сравните время следующего матча - оно должно обновиться")
        print("=" * 80)

if __name__ == "__main__":
    test_schedule_recalculation()




