FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app:create_app
ENV PYTHONUNBUFFERED=1

EXPOSE 10000

CMD gunicorn -w 2 -b 0.0.0.0:${PORT:-10000} 'app:create_app()'
