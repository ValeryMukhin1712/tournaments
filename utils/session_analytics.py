"""
Система аналитики и статистики сессий
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_
from collections import defaultdict

logger = logging.getLogger(__name__)

class SessionAnalytics:
    """Класс для анализа и статистики сессий"""
    
    def __init__(self, db, UserActivity):
        self.db = db
        self.UserActivity = UserActivity
    
    def get_daily_sessions_stats(self, date_from=None, date_to=None):
        """
        Получает статистику сессий по дням
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика по дням
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            # Статистика по дням
            daily_stats = self.db.session.query(
                func.date(self.UserActivity.created_at).label('date'),
                func.count(self.UserActivity.id).label('total_sessions'),
                func.count(func.distinct(self.UserActivity.email)).label('unique_users'),
                func.avg(self.UserActivity.session_duration).label('avg_duration')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to
                )
            ).group_by(
                func.date(self.UserActivity.created_at)
            ).order_by('date').all()
            
            result = []
            for stat in daily_stats:
                result.append({
                    'date': stat.date.isoformat() if stat.date else None,
                    'total_sessions': stat.total_sessions or 0,
                    'unique_users': stat.unique_users or 0,
                    'avg_duration': round(stat.avg_duration or 0, 2)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении дневной статистики: {e}")
            return []
    
    def get_user_sessions_stats(self, email=None, date_from=None, date_to=None):
        """
        Получает статистику сессий по пользователям
        
        Args:
            email (str): Email пользователя (опционально)
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика по пользователям
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            query = self.db.session.query(
                self.UserActivity.email,
                func.count(self.UserActivity.id).label('total_sessions'),
                func.avg(self.UserActivity.session_duration).label('avg_duration'),
                func.sum(self.UserActivity.pages_visited_count).label('total_pages'),
                func.max(self.UserActivity.last_activity).label('last_activity')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to
                )
            )
            
            if email:
                query = query.filter(self.UserActivity.email == email)
            
            user_stats = query.group_by(
                self.UserActivity.email
            ).order_by(
                func.count(self.UserActivity.id).desc()
            ).all()
            
            result = []
            for stat in user_stats:
                result.append({
                    'email': stat.email,
                    'total_sessions': stat.total_sessions or 0,
                    'avg_duration': round(stat.avg_duration or 0, 2),
                    'total_pages': stat.total_pages or 0,
                    'last_activity': stat.last_activity.isoformat() if stat.last_activity else None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики пользователей: {e}")
            return []
    
    def get_session_duration_stats(self, date_from=None, date_to=None):
        """
        Получает статистику продолжительности сессий
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика продолжительности
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            # Общая статистика (без percentile_cont для совместимости с SQLite)
            stats = self.db.session.query(
                func.count(self.UserActivity.id).label('total_sessions'),
                func.avg(self.UserActivity.session_duration).label('avg_duration'),
                func.min(self.UserActivity.session_duration).label('min_duration'),
                func.max(self.UserActivity.session_duration).label('max_duration')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to,
                    self.UserActivity.session_duration.isnot(None)
                )
            ).first()
            
            # Вычисляем медиану отдельно для SQLite
            median_duration = None
            if stats and stats.total_sessions > 0:
                durations = self.db.session.query(self.UserActivity.session_duration).filter(
                    and_(
                        self.UserActivity.user_type == 'admin',
                        self.UserActivity.created_at >= date_from,
                        self.UserActivity.created_at <= date_to,
                        self.UserActivity.session_duration.isnot(None)
                    )
                ).order_by(self.UserActivity.session_duration).all()
                
                if durations:
                    durations_list = [d[0] for d in durations]
                    n = len(durations_list)
                    if n % 2 == 0:
                        median_duration = (durations_list[n//2-1] + durations_list[n//2]) / 2
                    else:
                        median_duration = durations_list[n//2]
            
            # Распределение по диапазонам
            ranges = [
                (0, 300, '0-5 мин'),
                (300, 900, '5-15 мин'),
                (900, 1800, '15-30 мин'),
                (1800, 3600, '30-60 мин'),
                (3600, 7200, '1-2 часа'),
                (7200, None, 'более 2 часов')
            ]
            
            range_stats = []
            for min_dur, max_dur, label in ranges:
                query = self.db.session.query(
                    func.count(self.UserActivity.id)
                ).filter(
                    and_(
                        self.UserActivity.user_type == 'admin',
                        self.UserActivity.created_at >= date_from,
                        self.UserActivity.created_at <= date_to,
                        self.UserActivity.session_duration >= min_dur
                    )
                )
                
                if max_dur is not None:
                    query = query.filter(self.UserActivity.session_duration < max_dur)
                
                count = query.scalar() or 0
                range_stats.append({
                    'range': label,
                    'count': count
                })
            
            return {
                'total_sessions': stats.total_sessions or 0,
                'avg_duration': round(stats.avg_duration or 0, 2),
                'min_duration': stats.min_duration or 0,
                'max_duration': stats.max_duration or 0,
                'median_duration': round(median_duration or 0, 2),
                'duration_ranges': range_stats
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики продолжительности: {e}")
            return {}
    
    def get_termination_reasons_stats(self, date_from=None, date_to=None):
        """
        Получает статистику причин завершения сессий
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика причин завершения
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            reason_stats = self.db.session.query(
                self.UserActivity.logout_reason,
                func.count(self.UserActivity.id).label('count')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to,
                    self.UserActivity.logout_reason.isnot(None)
                )
            ).group_by(
                self.UserActivity.logout_reason
            ).all()
            
            result = []
            total = sum(stat.count for stat in reason_stats)
            
            for stat in reason_stats:
                percentage = round((stat.count / total * 100), 2) if total > 0 else 0
                result.append({
                    'reason': stat.logout_reason,
                    'count': stat.count,
                    'percentage': percentage
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики причин завершения: {e}")
            return []
    
    def get_peak_hours_stats(self, date_from=None, date_to=None):
        """
        Получает статистику пиковых часов активности
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика по часам
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            hour_stats = self.db.session.query(
                func.extract('hour', self.UserActivity.created_at).label('hour'),
                func.count(self.UserActivity.id).label('count')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to
                )
            ).group_by(
                func.extract('hour', self.UserActivity.created_at)
            ).order_by('hour').all()
            
            # Создаем полный список часов (0-23)
            hours_data = {i: 0 for i in range(24)}
            for stat in hour_stats:
                hours_data[int(stat.hour)] = stat.count
            
            result = []
            for hour in range(24):
                result.append({
                    'hour': hour,
                    'count': hours_data[hour],
                    'label': f"{hour:02d}:00"
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики пиковых часов: {e}")
            return []
    
    def get_geographic_stats(self, date_from=None, date_to=None):
        """
        Получает статистику по IP адресам (географическая статистика)
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика по IP адресам
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            ip_stats = self.db.session.query(
                self.UserActivity.ip_address,
                func.count(self.UserActivity.id).label('count'),
                func.count(func.distinct(self.UserActivity.email)).label('unique_users')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to,
                    self.UserActivity.ip_address.isnot(None)
                )
            ).group_by(
                self.UserActivity.ip_address
            ).order_by(
                func.count(self.UserActivity.id).desc()
            ).limit(20).all()
            
            result = []
            for stat in ip_stats:
                result.append({
                    'ip_address': stat.ip_address,
                    'count': stat.count,
                    'unique_users': stat.unique_users
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении географической статистики: {e}")
            return []
    
    def get_page_visit_stats(self, date_from=None, date_to=None):
        """
        Получает статистику посещений страниц
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Статистика посещений страниц
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            page_stats = self.db.session.query(
                self.UserActivity.last_page,
                func.count(self.UserActivity.id).label('count'),
                func.avg(self.UserActivity.pages_visited_count).label('avg_pages_per_session')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to,
                    self.UserActivity.last_page.isnot(None)
                )
            ).group_by(
                self.UserActivity.last_page
            ).order_by(
                func.count(self.UserActivity.id).desc()
            ).limit(20).all()
            
            result = []
            for stat in page_stats:
                result.append({
                    'page': stat.last_page,
                    'count': stat.count,
                    'avg_pages_per_session': round(stat.avg_pages_per_session or 0, 2)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при получении статистики посещений страниц: {e}")
            return []
    
    def get_overall_statistics(self, date_from=None, date_to=None):
        """
        Получает общую статистику
        
        Args:
            date_from (datetime): Начальная дата
            date_to (datetime): Конечная дата
            
        Returns:
            dict: Общая статистика
        """
        try:
            if not date_from:
                date_from = datetime.utcnow() - timedelta(days=30)
            if not date_to:
                date_to = datetime.utcnow()
            
            # Общая статистика
            overall_stats = self.db.session.query(
                func.count(self.UserActivity.id).label('total_sessions'),
                func.count(func.distinct(self.UserActivity.email)).label('unique_users'),
                func.avg(self.UserActivity.session_duration).label('avg_duration'),
                func.sum(self.UserActivity.pages_visited_count).label('total_pages'),
                func.count(
                    self.UserActivity.id
                ).filter(
                    self.UserActivity.is_terminated == True
                ).label('terminated_sessions')
            ).filter(
                and_(
                    self.UserActivity.user_type == 'admin',
                    self.UserActivity.created_at >= date_from,
                    self.UserActivity.created_at <= date_to
                )
            ).first()
            
            # Топ-5 самых активных пользователей
            top_users = self.get_user_sessions_stats(date_from=date_from, date_to=date_to)[:5]
            
            return {
                'total_sessions': overall_stats.total_sessions or 0,
                'unique_users': overall_stats.unique_users or 0,
                'avg_duration': round(overall_stats.avg_duration or 0, 2),
                'total_pages': overall_stats.total_pages or 0,
                'terminated_sessions': overall_stats.terminated_sessions or 0,
                'top_users': top_users,
                'date_from': date_from.isoformat() if date_from else None,
                'date_to': date_to.isoformat() if date_to else None
            }
            
        except Exception as e:
            logger.error(f"Ошибка при получении общей статистики: {e}")
            return {}


def create_session_analytics(db, UserActivity):
    """Создает экземпляр SessionAnalytics"""
    return SessionAnalytics(db, UserActivity)

