FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ .

EXPOSE 8080
CMD ["python", "app.py"]
