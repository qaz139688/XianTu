FROM python:3.12-slim

WORKDIR /app

COPY server/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY server ./server

ENV XIANTU_DB_PATH=/data/xiantu.db
EXPOSE 12345

CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "12345"]
