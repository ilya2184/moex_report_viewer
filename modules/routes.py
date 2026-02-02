# modules/routes.py
from flask import render_template, request, send_file, jsonify, redirect, url_for
import os
from datetime import datetime
from .converter import MOEXConverter
from .utils import allowed_file, TemporaryFileManager, generate_filename

def register_routes(app, converter, temp_manager):
    """Регистрация маршрутов приложения"""
    
    @app.route('/')
    def index():
        """Главная страница"""
        return render_template('index.html')
    
    @app.route('/upload', methods=['POST'])
    def upload_file():
        """Обработка загрузки файла"""
        if 'xml_file' not in request.files:
            return render_template('error.html', 
                                 error="Файл не загружен"), 400
        
        file = request.files['xml_file']
        
        if file.filename == '':
            return render_template('error.html',
                                 error="Файл не выбран"), 400
        
        if not allowed_file(file.filename):
            return render_template('error.html',
                                 error="Недопустимый формат файла. Разрешены только .xml"), 400
        
        try:
            # Читаем файл
            xml_bytes = file.read()
            
            # Проверяем размер
            if len(xml_bytes) > app.config['MAX_CONTENT_LENGTH']:
                return render_template('error.html',
                                     error=f"Файл слишком большой. Максимальный размер: "
                                           f"{app.config['MAX_CONTENT_LENGTH'] // (1024*1024)}MB"), 400
            
            # Конвертируем
            html_content, xslt_used = converter.convert(xml_bytes)
            
            # Сохраняем во временный файл
            temp_id, filename, filepath = temp_manager.create_temp_file(
                html_content, 
                extension='.html',
                prefix='moex_'
            )
            
            # Записываем информацию о файле в сессию
            file_info = {
                'original_name': file.filename,
                'converted_name': filename,
                'temp_id': temp_id,
                'timestamp': datetime.now().isoformat(),
                'xslt_used': xslt_used
            }
            
            # Перенаправляем на страницу результата
            return redirect(url_for('show_result', temp_id=temp_id))
            
        except Exception as e:
            app.logger.error(f"Ошибка конвертации: {str(e)}")
            return render_template('error.html',
                                 error=f"Ошибка при обработке файла: {str(e)}"), 500
    
    @app.route('/result/<temp_id>')
    def show_result(temp_id):
        """Отображение результата конвертации"""
        filepath = temp_manager.get_temp_file(temp_id)
        
        if not filepath or not os.path.exists(filepath):
            return render_template('error.html',
                                 error="Файл не найден или устарел"), 404
        
        # Читаем HTML результат
        with open(filepath, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return render_template('result.html',
                             html_content=html_content,
                             temp_id=temp_id)
    
    @app.route('/download/<temp_id>')
    def download_file(temp_id):
        """Скачивание сконвертированного файла"""
        filepath = temp_manager.get_temp_file(temp_id)
        
        if not filepath or not os.path.exists(filepath):
            return render_template('error.html',
                                 error="Файл не найден или устарел"), 404
        
        # Генерируем имя для скачивания
        original_name = request.args.get('name', 'converted')
        download_name = generate_filename(original_name, suffix='converted')
        # Всегда предлагаем скачивание именно как HTML файл
        base, ext = os.path.splitext(download_name)
        if ext.lower() != '.html':
            download_name = f"{base}.html"
        
        return send_file(
            filepath,
            as_attachment=True,
            download_name=download_name,
            mimetype='text/html'
        )
    
    @app.route('/api/convert', methods=['POST'])
    def api_convert():
        """API endpoint для конвертации"""
        if 'xml_file' not in request.files:
            return jsonify({'error': 'Файл не загружен'}), 400
        
        file = request.files['xml_file']
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Недопустимый формат файла'}), 400
        
        try:
            xml_bytes = file.read()
            html_content, xslt_used = converter.convert(xml_bytes)
            
            # Создаем временный файл
            temp_id, filename, filepath = temp_manager.create_temp_file(html_content)
            
            return jsonify({
                'success': True,
                'temp_id': temp_id,
                'download_url': url_for('download_file', temp_id=temp_id, _external=True),
                'preview_url': url_for('show_result', temp_id=temp_id, _external=True),
                'xslt_used': xslt_used
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/validate', methods=['POST'])
    def api_validate():
        """API для валидации XML"""
        if 'xml_file' not in request.files:
            return jsonify({'error': 'Файл не загружен'}), 400
        
        file = request.files['xml_file']
        xml_bytes = file.read()
        
        is_valid, message = converter.validate_xml(xml_bytes)
        
        return jsonify({
            'valid': is_valid,
            'message': message
        })
    
    @app.route('/cleanup', methods=['POST'])
    def cleanup():
        """Очистка временных файлов (требуется аутентификация в продакшене)"""
        if not app.debug and not request.headers.get('X-Admin-Key') == app.config.get('ADMIN_KEY'):
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        deleted = temp_manager.cleanup()
        return jsonify({
            'success': True,
            'deleted': deleted
        })
    
    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html',
                             error="Страница не найдена"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f"Internal server error: {error}")
        return render_template('error.html',
                             error="Внутренняя ошибка сервера"), 500