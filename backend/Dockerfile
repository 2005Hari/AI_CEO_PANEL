FROM python:3.11-slim

WORKDIR /app

# Layer dependency install separately from app code for better build caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1001 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Database schema is brought up to date on startup by app/main.py's lifespan
# (Base.metadata.create_all for USE_SQLITE, `alembic upgrade head` otherwise) —
# no separate migration step needed here.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
