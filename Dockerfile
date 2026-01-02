FROM python:3.12-slim

WORKDIR /app

# Копируем файлы проекта
COPY app/requirements.txt requirements.txt
COPY app/ app/
COPY static/ static/
COPY README.md README.md

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Запускаем bot.py (он использует polling для Telegram)
# или можно запустить FastAPI сервер если нужен веб-интерфейс
CMD ["python", "app/bot.py"]
