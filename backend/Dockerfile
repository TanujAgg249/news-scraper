FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Use deploy-requirements.txt which excludes heavy ML libs (sentence-transformers/PyTorch)
COPY deploy-requirements.txt .
RUN pip install --no-cache-dir -r deploy-requirements.txt

# Copy application code
COPY . .

# Render sets the PORT environment variable — default to 8000 for local use
ENV PORT=8000

# Mark this as a cloud deployment (disables heavy ML models)
ENV RENDER=true

# Run the FastAPI app with uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
