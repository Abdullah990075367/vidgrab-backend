FROM python:3.11-slim

# FFmpeg install (video+audio merge ke liye zaroori)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Render PORT env variable set karta hai
ENV PORT=10000

EXPOSE 10000

CMD gunicorn --bind 0.0.0.0:$PORT --timeout 600 --workers 1 app:app