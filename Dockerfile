FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["/bin/sh", "-c", "python init_db.py && uvicorn api:app --host 0.0.0.0 --port 8000 & python bot.py"]
