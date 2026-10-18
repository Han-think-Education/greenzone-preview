FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend /app/backend
COPY preview /app/preview
COPY data /app/data
COPY scripts/index_knowledge.py /app/scripts/index_knowledge.py
RUN mkdir -p /app/storage
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
