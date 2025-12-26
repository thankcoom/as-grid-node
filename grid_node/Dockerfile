# ═══════════════════════════════════════════════════════════════════════════
# AS Grid Node - Zeabur Deployment
#
# Build context: bitget_as/ (parent directory)
# Build command: docker build -f grid_node/Dockerfile -t grid-node .
# ═══════════════════════════════════════════════════════════════════════════

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for TA-Lib and other packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    wget \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Install Python dependencies
COPY grid_node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY trading_core /app/trading_core
COPY coin_selection /app/coin_selection
COPY asBack /app/asBack

# Copy grid_node app
COPY grid_node/app /app/app

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Expose port
EXPOSE 8000

# Run with uvicorn (use python -m to ensure it's found)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
