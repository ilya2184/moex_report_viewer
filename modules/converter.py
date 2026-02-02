# modules/converter.py
import re
import io
from lxml import etree
import requests
from urllib.parse import urljoin
from .utils import extract_encoding_from_xml, fix_encoding_issues

class MOEXConverter:
    """Конвертер XML MOEX в HTML"""
    
    def __init__(self, xslt_base_url, xsd_base_url=None, timeout=30):
        self.xslt_base_url = xslt_base_url
        self.xsd_base_url = xsd_base_url
        self.timeout = timeout
        
    def extract_xslt_urls(self, xml_doc):
        """Извлечение URL XSLT из XML документа"""
        xslt_urls = []
        
        for node in xml_doc.xpath('//processing-instruction()'):
            if node.target == 'xml-stylesheet':
                pi_text = str(node)
                match = re.search(r'href=[\'"]([^\'"]+)[\'"]', pi_text)
                if match:
                    href = match.group(1)
                    
                    # Преобразование локальных путей в URL
                    if href.startswith('C:\\MICEX\\XSLT\\'):
                        filename = href.split('\\')[-1]
                        href = urljoin(self.xslt_base_url, filename)
                    elif href.startswith('C:\\MICEX\\XSD\\') and self.xsd_base_url:
                        filename = href.split('\\')[-1]
                        href = urljoin(self.xsd_base_url, filename)
                    
                    xslt_urls.append(href)
        
        return xslt_urls
    
    def load_xslt(self, xslt_url):
        """Загрузка XSLT файла"""
        try:
            response = requests.get(xslt_url, timeout=self.timeout)
            response.raise_for_status()
            content = response.content
            
            # Определение кодировки XSLT
            encoding = 'utf-8'
            header = content[:200].decode('ascii', errors='ignore')
            match = re.search(r'encoding=[\'"]([^\'"]+)[\'"]', header)
            if match:
                encoding = match.group(1).lower()
            
            return content, encoding
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ошибка загрузки XSLT: {e}")
    
    def decode_xml(self, xml_bytes):
        """Декодирование XML с правильной кодировкой"""
        encoding = extract_encoding_from_xml(xml_bytes)
        
        # Пробуем декодировать с найденной кодировкой
        for enc in [encoding, 'windows-1251', 'cp1251', 'utf-8']:
            try:
                return xml_bytes.decode(enc), enc
            except UnicodeDecodeError:
                continue
        
        # Если ничего не сработало, используем игнорирование ошибок
        return xml_bytes.decode('utf-8', errors='ignore'), 'utf-8'
    
    def convert(self, xml_bytes, xslt_url=None):
        """Основной метод конвертации"""
        # Шаг 1: Декодируем XML
        xml_text, xml_encoding = self.decode_xml(xml_bytes)
        
        # Шаг 2: Парсим XML
        parser = etree.XMLParser(encoding=xml_encoding)
        xml_file_like = io.BytesIO(xml_bytes)
        
        try:
            xml_doc = etree.parse(xml_file_like, parser=parser)
        except Exception as e:
            # Альтернативный способ парсинга
            xml_doc = etree.fromstring(xml_text.encode('utf-8'))
        
        # Шаг 3: Получаем URL XSLT
        xslt_urls = self.extract_xslt_urls(xml_doc)
        
        if not xslt_urls and not xslt_url:
            # Используем стандартный XSLT
            default_xslt = "CCX99_RU_23062025.xsl"
            xslt_url = urljoin(self.xslt_base_url, default_xslt)
            xslt_urls = [xslt_url]
        elif xslt_url:
            xslt_urls.insert(0, xslt_url)
        
        # Шаг 4: Загружаем и применяем XSLT
        last_error = None
        for url in xslt_urls:
            try:
                xslt_content, xslt_encoding = self.load_xslt(url)
                
                # Парсим XSLT
                try:
                    xslt_doc = etree.parse(
                        io.BytesIO(xslt_content),
                        parser=etree.XMLParser(encoding=xslt_encoding)
                    )
                except Exception:
                    xslt_doc = etree.parse(io.BytesIO(xslt_content))
                
                # Применяем преобразование
                transform = etree.XSLT(xslt_doc)
                result = transform(xml_doc)
                html_output = str(result)
                
                # Исправляем проблемы с кодировкой
                html_output = fix_encoding_issues(html_output)
                
                return html_output, url
                
            except Exception as e:
                last_error = e
                continue
        
        # Если ни один XSLT не сработал
        if last_error:
            raise Exception(f"Не удалось применить ни один XSLT. Последняя ошибка: {last_error}")
        else:
            raise Exception("Не найден подходящий XSLT для преобразования")
    
    def validate_xml(self, xml_bytes, xsd_url=None):
        """Валидация XML по XSD схеме (опционально)"""
        try:
            xml_text, _ = self.decode_xml(xml_bytes)
            xml_doc = etree.fromstring(xml_text.encode('utf-8'))
            
            if xsd_url:
                # Загружаем XSD схему
                response = requests.get(xsd_url, timeout=self.timeout)
                xsd_content = response.content
                
                # Создаем XML схему
                xsd_doc = etree.XML(xsd_content)
                schema = etree.XMLSchema(xsd_doc)
                
                # Валидируем
                schema.assertValid(xml_doc)
            
            return True, "XML валиден"
            
        except etree.XMLSyntaxError as e:
            return False, f"Ошибка синтаксиса XML: {e}"
        except etree.DocumentInvalid as e:
            return False, f"XML не соответствует схеме: {e}"
        except Exception as e:
            return False, f"Ошибка валидации: {e}"