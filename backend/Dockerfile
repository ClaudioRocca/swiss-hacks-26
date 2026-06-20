FROM python:3.11-slim

WORKDIR /app

# Install system deps for chromadb (sqlite, build tools)
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .
COPY src/ src/
COPY client_calls/ client_calls/

EXPOSE 8080

CMD ["python", "server.py"]
