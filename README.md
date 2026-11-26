# AI генератор сайтов

Веб-сайт на FastAPI для генерирации HTML-страниц по текстовому промпту с помощью ИИ.

## Какие сервисы используются

| Сервис | Назначение |
|--------|-----------|
| **Deepseek** (через [html_page_generator](https://github.com/devmanorg/html-page-generator)) | Генерация HTML-кода по промпту |
| **Unsplash** (через [html_page_generator](https://github.com/devmanorg/html-page-generator)) | Подбор изображений для сайта по тематике запроса |
| **MinIO / S3** | Хранение HTML-файлов и скриншотов, публичная раздача |
| **Gotenberg** ([gotenberg-api](https://github.com/devmanorg/gotenberg-api)) | Рендеринг скриншота HTML-страницы |

## Репозиторий для бэкенд-разработчиков

Инструкции и справочная информация по разворачиванию локальной инсталляции собраны
в документе [CONTRIBUTING.md](./CONTRIBUTING.md).

### Переменные окружения

В файле-шаблоне `example.env` перечислены все необходимые переменные окружения. Создайте файл `.env` и скопируйте в него содержимое файла-шаблона, заменив значения переменных на реальные. Файл `.env` должен быть добавлен в `.gitignore`.

Ключи для сервисов:
- `DEEPSEEK__API_KEY` - для генерации HTML-кода по запросу пользователя потребуется оплатить доступ к серверам [API DeepSeek](https://api-docs.deepseek.com/quick_start/pricing) и получить ключ доступа.
- `UNSPLASH__CLIENT_ID` - Unsplash API ключ доступа для поиска изображений в фотостоке. Необходимо зарегестрировать аккаунт по [ссылке](https://unsplash.com/documentation#creating-a-developer-account), создать [demo-приложение](https://unsplash.com/oauth/applications) и получить ключ.

Если вы используете альтернативную инсталляцию DeepSeek, то необходимо также указать её URL-адрес и, если это необходимо, другую LLM-модель:
- `DEEPSEEK__BASE_URL` - URL-адрес альтернативной инсталляции для запросов к API.
Если не указан, то по-умолчанию используется https://api.deepseek.com/v1.
- `DEEPSEEK__MODEL` - название альтернативной модели. Если не указано, то по-умолчанию используется модель deepseek-chat.

S3 хранилище MinIO (см. [CONTRIBUTING.md](./CONTRIBUTING.md), чтобы узнать подробнее):
- `S3__ENDPOINT_URL` - API-порт MinIO
- `S3__ACCESS_KEY` - имя пользователя MinIO
- `S3__SECRET_KEY` - пароль MinIO
- `S3__BUCKET` - название бакета