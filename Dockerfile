# FOCEYE Production Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Ensure unbuffered python output for real-time production logging
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Install system dependencies for OpenCV, Headless Graphics, and ReportLab
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose default Render port
EXPOSE 10000

# Start Uvicorn ASGI production server binding to 0.0.0.0 and dynamic PORT
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
