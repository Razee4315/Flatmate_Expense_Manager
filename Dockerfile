# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV FLASK_APP=run.py \
    FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Create necessary directories and set permissions
RUN python create_dirs.py \
    && chmod -R 755 /app

# Create a non-root user and switch to it
RUN useradd -m myuser \
    && chown -R myuser:myuser /app
USER myuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Run the application
CMD ["flask", "run", "--host=0.0.0.0"]
