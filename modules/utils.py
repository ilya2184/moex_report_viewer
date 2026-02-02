# modules/utils.py
import re
import os
import uuid
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def generate_filename(original_name, suffix=''):
    """Генерация уникального имени файла"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    name, ext = os.path.splitext(original_name)
    unique_id = str(uuid.uuid4())[:8]
    
    if suffix:
        return f"{name}_{suffix}_{timestamp}_{unique_id}{ext}"
    return f"{name}_{timestamp}_{unique_id}{ext}"

def allowed_file(filename, allowed_extensions=None):
    """Проверка расширения файла"""
    if allowed_extensions is None:
        allowed_extensions = {'.xml'}
    
    return '.' in filename and \
           Path(filename).suffix.lower() in allowed_extensions

def cleanup_old_files(directory, max_age_hours=1):
    """Удаление старых файлов"""
    if not os.path.exists(directory):
        return 0
    
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
    deleted_count = 0
    
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        try:
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_mtime < cutoff_time:
                os.remove(filepath)
                deleted_count += 1
        except (OSError, Exception):
            continue
    
    return deleted_count

def extract_encoding_from_xml(xml_bytes):
    """Извлечение кодировки из заголовка XML"""
    try:
        header = xml_bytes[:100].decode('ascii', errors='ignore')
        match = re.search(r'encoding=[\'"]([^\'"]+)[\'"]', header)
        if match:
            return match.group(1).lower()
    except Exception:
        pass
    return 'windows-1251'  # значение по умолчанию для MOEX

def fix_encoding_issues(text):
    """Исправление проблем с кодировкой"""
    # Базовые замены для исправления двойной кодировки
    replacements = {
        'РЎ': 'С', 'Рћ': 'О', 'Р': '', 'С': 'С',
        'вЂњ': '"', 'вЂќ': '"', 'вЂ"': '-',
        'вЂ™': "'", 'вЂ"': '—', 'вЂ"': '–'
    }
    
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)
    
    # Исправление двойной кодировки windows-1251 -> utf-8 -> windows-1251
    def decode_double_encoded(match):
        try:
            return match.group(0).encode('utf-8').decode('windows-1251')
        except:
            return match.group(0)
    
    # Ищем последовательности, похожие на двойную кодировку
    pattern = r'[А-Яа-яРСТУФХЦЧШЩЪЫЬЭЮЯ]{2,}'
    text = re.sub(pattern, decode_double_encoded, text)
    
    return text

class TemporaryFileManager:
    """Менеджер временных файлов"""
    
    def __init__(self, temp_dir):
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
    
    def create_temp_file(self, content, extension='.html', prefix='moex_'):
        """Создание временного файла"""
        temp_id = str(uuid.uuid4())
        filename = f"{prefix}{temp_id}{extension}"
        filepath = os.path.join(self.temp_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return temp_id, filename, filepath
    
    def get_temp_file(self, temp_id, prefix='moex_'):
        """Получение пути к временному файлу по ID"""
        for filename in os.listdir(self.temp_dir):
            if filename.startswith(prefix) and temp_id in filename:
                return os.path.join(self.temp_dir, filename)
        return None
    
    def cleanup(self, max_age_hours=1):
        """Очистка старых файлов"""
        return cleanup_old_files(self.temp_dir, max_age_hours)
    
    def delete_file(self, temp_id, prefix='moex_'):
        """Удаление файла по ID"""
        filepath = self.get_temp_file(temp_id, prefix)
        if filepath and os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False