# MOEX XML Converter

Веб-сервис для преобразования XML отчётов Московской Биржи в HTML формат.

## Возможности

- Конвертация XML файлов MOEX в HTML
- Автоматическое определение кодировки (Windows-1251, UTF-8)
- Загрузка необходимых XSLT стилей с серверов MOEX
- Удобный интерфейс с drag & drop
- Возможность скачивания и печати результатов
- API для интеграции

## Быстрый старт

### Установка и запуск через Docker

```bash
# Клонирование репозитория
git clone <repository-url>
cd moex_converter

# Сборка Docker образа
docker build -t moex-converter .

# Запуск контейнера
docker run -p 5050:5050 moex-converter
```

После запуска сервис будет доступен по адресу: `http://localhost:5050`

## API Документация

### Веб-интерфейс

#### `GET /`
Главная страница с интерфейсом загрузки файлов.

#### `POST /upload`
Загрузка XML файла через веб-интерфейс.

**Параметры:**
- `xml_file` (multipart/form-data) - XML файл для конвертации

**Ответ:**
- При успехе: редирект на `/result/<temp_id>`
- При ошибке: HTML страница с описанием ошибки (400/500)

#### `GET /result/<temp_id>`
Просмотр результата конвертации.

**Параметры:**
- `temp_id` (path) - идентификатор временного файла
- `?print` (query, опционально) - автоматический запуск печати

**Ответ:** HTML страница с результатом конвертации

#### `GET /download/<temp_id>`
Скачивание сконвертированного HTML файла.

**Параметры:**
- `temp_id` (path) - идентификатор временного файла
- `name` (query, опционально) - имя файла для скачивания

**Ответ:** HTML файл с заголовком `Content-Disposition: attachment`

### REST API

#### `POST /api/convert`
Конвертация XML файла в HTML через API.

**Параметры:**
- `xml_file` (multipart/form-data) - XML файл для конвертации

**Ответ (200 OK):**
```json
{
  "success": true,
  "temp_id": "uuid-here",
  "download_url": "http://host/download/uuid-here",
  "preview_url": "http://host/result/uuid-here",
  "xslt_used": "https://ftp.moex.com/pub/Reports/Currency/XSLT/CCX99_RU_23062025.xsl"
}
```

**Ошибки:**
- `400` - файл не загружен или недопустимый формат
- `500` - ошибка при обработке файла

**Пример использования:**
```bash
curl -X POST -F "xml_file=@report.xml" http://localhost:5050/api/convert
```

#### `POST /api/validate`
Валидация XML файла.

**Параметры:**
- `xml_file` (multipart/form-data) - XML файл для валидации

**Ответ (200 OK):**
```json
{
  "valid": true,
  "message": "XML валиден"
}
```

или при ошибке:
```json
{
  "valid": false,
  "message": "Ошибка синтаксиса XML: ..."
}
```

**Пример использования:**
```bash
curl -X POST -F "xml_file=@report.xml" http://localhost:5050/api/validate
```

#### `POST /cleanup`
Очистка временных файлов (требует аутентификации в продакшене).

**Заголовки:**
- `X-Admin-Key` (требуется в продакшене) - ключ администратора

**Ответ (200 OK):**
```json
{
  "success": true,
  "deleted": 5
}
```

**Ошибки:**
- `403` - доступ запрещен (в продакшене без правильного ключа)

**Пример использования:**
```bash
curl -X POST -H "X-Admin-Key: your-admin-key" http://localhost:5050/cleanup
```

## Ограничения

- Максимальный размер файла: 16 MB
- Поддерживаемые форматы: `.xml`
- Временные файлы автоматически удаляются через 1 час
- В продакшене требуется установка переменной окружения `SECRET_KEY`
