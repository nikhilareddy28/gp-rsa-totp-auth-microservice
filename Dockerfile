FROM python:3.12-slim AS runtime

ENV TZ=UTC
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

VOLUME ["/data", "/cron"]

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
