FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY grid_node/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared modules
COPY trading_core /app/trading_core
COPY coin_selection /app/coin_selection
COPY asBack /app/asBack

# Copy grid_node app
COPY grid_node/app /app/app

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

