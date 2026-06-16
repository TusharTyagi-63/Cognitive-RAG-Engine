FROM python:3.11-slim

# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE 1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install system dependencies required for compilation (e.g. for building C-extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --default-timeout=1000 --retries=15 -r requirements.txt

# Copy the backend source code
COPY backend/ ./backend/
# Copy the alembic configuration and migrations
COPY alembic.ini .
COPY alembic/ ./alembic/

# Expose the FastAPI port
EXPOSE 8000

# Run Alembic migrations and then start the Uvicorn server
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
