# config.py
import os
from pathlib import Path

basedir = Path(__file__).parent.absolute()

class Config:
    # Основные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Пути
    UPLOAD_FOLDER = os.path.join(basedir, 'temp_uploads')
    STATIC_FOLDER = os.path.join(basedir, 'static')
    TEMPLATE_FOLDER = os.path.join(basedir, 'templates')
    
    # MOEX URLs
    MOEX_XSLT_BASE = "https://ftp.moex.com/pub/Reports/Currency/XSLT"
    MOEX_XSD_BASE = "https://ftp.moex.com/pub/Reports/Currency/XSD"
    
    # Время жизни временных файлов (в секундах)
    TEMP_FILE_LIFETIME = 3600  # 1 час
    
    # Настройки запросов
    REQUEST_TIMEOUT = 30
    ALLOWED_EXTENSIONS = {'.xml'}
    
    @staticmethod
    def init_app(app):
        # Создаем необходимые директории
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)
        os.makedirs(app.config['TEMPLATE_FOLDER'], exist_ok=True)

class DevelopmentConfig(Config):
    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True

class ProductionConfig(Config):
    DEBUG = False
    # В продакшене используем более безопасные настройки
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY не установлен в переменных окружения")
    
    # Можно использовать Redis или другую БД для сессий
    # SESSION_TYPE = 'redis'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}