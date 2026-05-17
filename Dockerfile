FROM python:3.14-slim

WORKDIR /app

RUN pip install uv
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
 && rm -rf /var/lib/apt/lists/*
 
COPY . .

RUN uv sync

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Command to run the application
CMD ["uv", "run", "main.py"]