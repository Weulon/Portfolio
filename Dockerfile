FROM python:3.12-slim

WORKDIR /app

# Копируем файлы проекта
COPY app/requirements.txt requirements.txt
COPY app/ app/
COPY static/ static/
COPY README.md README.md

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# По умолчанию запускаем FastAPI сайт (uvicorn). Для запуска бота
# в Render создайте отдельный Background Worker с командой
# `python app/bot.py` (scale=1), чтобы избежать конфликтов polling.
CMD ["sh", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
