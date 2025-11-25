"""
Принудительное обновление времени следующего матча на основе времени окончания предыдущего.
Использовать если пересчет не сработал автоматически.
"""
from app import app, db
from models.match import Match
from models.tournament import Tournament
from datetime import datetime, timedelta

def force_recalc(tournament_id=17):
    """Принудительный пересчет всех следующих матчей для завершенных"""
    
    with app.app_context():
        tournament = Tournament.query.get(tournament_id)
        if not tournament:
            print(f"❌ Турнир с ID {tournament_id} не найден")
            return
        
        print(f"📋 Турнир: {tournament.name}")
        print(f"Длительность матча: {tournament.match_duration or 15} мин")
        print(f"Перерыв: {tournament.break_duration or 2} мин")
        print("=" * 60)
        
        # Получаем все завершенные матчи, отсортированные по времени окончания
        completed_matches = Match.query.filter_by(
            tournament_id=tournament_id,
            status='завершен'
        ).order_by(
            Match.actual_end_time.asc() if Match.actual_end_time else Match.updated_at.asc()
        ).all()
        
        if not completed_matches:
            print("❌ Нет завершенных матчей")
            return
        
        print(f"✅ Найдено завершенных матчей: {len(completed_matches)}\n")
        
        updated_count = 0
        
        for completed_match in completed_matches:
            if not completed_match.actual_end_time:
                print(f"⚠️  Матч #{completed_match.match_number} не имеет actual_end_time, пропускаем")
                continue
            
            # Находим следующий незавершенный матч на той же площадке
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
            
            if not next_match:
                print(f"ℹ️  Нет следующих матчей на площадке {completed_match.court_number} после матча #{completed_match.match_number}")
                continue
            
            # Вычисляем новое время
            break_duration = tournament.break_duration or 2
            new_start_time = completed_match.actual_end_time + timedelta(minutes=break_duration)
            new_start_date = new_start_time.date()
            new_start_time_only = new_start_time.time()
            
            old_date = next_match.match_date
            old_time = next_match.match_time
            
            # Обновляем
            next_match.match_time = new_start_time_only
            next_match.match_date = new_start_date
            
            print(f"✅ Матч #{next_match.match_number}: {old_date} {old_time} -> {new_start_date} {new_start_time_only}")
            updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n✅ Обновлено матчей: {updated_count}")
        else:
            print("\nℹ️  Нет матчей для обновления")

if __name__ == "__main__":
    force_recalc(17)
















