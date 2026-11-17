FROM python:3.11-slim

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY src/ .

ENV QDRANT_PATH=:memory:
EXPOSE 5000

CMD ["sh", "-c", "python -c 'from database.database import init_db; init_db()' && gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 8 --timeout 180 main:app"]
