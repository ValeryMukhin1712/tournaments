"""
Модель для хранения настроек приложения
"""
from datetime import datetime
from . import db

class Settings(db.Model):
    __tablename__ = 'settings'
    __table_args__ = {'extend_existing': True}
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def __repr__(self):
        return f'<Settings {self.key}={self.value}>'
    
    @staticmethod
    def get_setting(key, default_value=None):
        """Получить значение настройки по ключу"""
        setting = Settings.query.filter_by(key=key).first()
        return setting.value if setting else default_value
    
    @staticmethod
    def set_setting(key, value, description=None):
        """Установить значение настройки"""
        setting = Settings.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.description = description
        else:
            setting = Settings(key=key, value=str(value), description=description)
            db.session.add(setting)
        db.session.commit()
        return setting