"""
Модель уведомления
"""
from datetime import datetime

def create_notification_model(db):
    """Создает модель Notification с переданным экземпляром db"""
    
    class Notification(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
        title = db.Column(db.String(100), nullable=False)
        message = db.Column(db.Text, nullable=False)
        is_read = db.Column(db.Boolean, default=False)
        created_at = db.Column(db.DateTime, default=datetime.utcnow)

        def __repr__(self):
            return f'<Notification {self.id} for User {self.user_id}>'
    
    return Notification
