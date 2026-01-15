# Multi-stage Python build for Intelligent Fund Onboarding Backend
FROM python:3.9 as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies including Docling requirements
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Create app user with proper home directory
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --home /home/appuser appuser && \
    mkdir -p /home/appuser && \
    chown appuser:appgroup /home/appuser

# Dependencies stage
FROM base as deps

# Copy requirements first for better caching
COPY ./backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM base as production

# Copy installed packages from deps stage
COPY --from=deps /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# Copy application code
COPY ./backend .
# Copy config file from root
COPY ./config.py .
# Copy src directory from root
COPY ./src ./src

# Create necessary directories including temp directories for Docling
RUN mkdir -p /app/data/uploads && \
    mkdir -p /app/data/downloads && \
    mkdir -p /app/logs && \
    mkdir -p /tmp/docling && \
    chmod 777 /tmp/docling

# Change ownership to app user and ensure write permissions
RUN chown -R appuser:appgroup /app /home/appuser && \
    chmod -R 755 /app && \
    chmod -R 755 /home/appuser

# Switch to app user
USER appuser

# Set environment variables for Docling
ENV HOME=/home/appuser \
    TMPDIR=/tmp/docling \
    XDG_CACHE_HOME=/home/appuser/.cache \
    XDG_DATA_HOME=/home/appuser/.local/share

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]