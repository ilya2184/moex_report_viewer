# app.py
import os
from flask import Flask
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Импорт конфигурации и модулей
from config import config
from modules.routes import register_routes
from modules.converter import MOEXConverter
from modules.utils import TemporaryFileManager

def create_app(config_name=None):
    """Фабрика приложения Flask"""
    
    # Создаем приложение
    app = Flask(__name__, 
                static_folder='static',
                template_folder='templates')
    
    # Загружаем конфигурацию
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # Инициализируем компоненты
    converter = MOEXConverter(
        xslt_base_url=app.config['MOEX_XSLT_BASE'],
        xsd_base_url=app.config.get('MOEX_XSD_BASE'),
        timeout=app.config['REQUEST_TIMEOUT']
    )
    
    temp_manager = TemporaryFileManager(app.config['UPLOAD_FOLDER'])
    
    # Регистрируем маршруты
    register_routes(app, converter, temp_manager)
    
    # Регистрируем обработчик для очистки временных файлов
    @app.before_request
    def cleanup_old_files():
        if app.debug:
            # В режиме разработки чистим при каждом запросе
            temp_manager.cleanup(app.config['TEMP_FILE_LIFETIME'] / 3600)
        else:
            # В продакшене чистим раз в 100 запросов
            import random
            if random.random() < 0.01:  # 1% шанс на очистку
                temp_manager.cleanup(app.config['TEMP_FILE_LIFETIME'] / 3600)
    
    return app

if __name__ == '__main__':
    # Создаем приложение
    app = create_app()
    
    # Запускаем сервер
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    print("=" * 60)
    print("MOEX Converter запущен!")
    print(f"Ссылка: http://{host}:{port}")
    print(f"Режим отладки: {'Включен' if debug else 'Выключен'}")
    print("=" * 60)
    
    app.run(host=host, port=port, debug=debug)