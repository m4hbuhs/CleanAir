FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (e.g., libgomp1 for XGBoost)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt
RUN pip install pydantic-settings==2.2.1


# Copy all backend source code
# Since this Dockerfile is in the backend/ directory, we copy the current context
COPY . /app/backend/

# Add backend directory to PYTHONPATH
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Start server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
