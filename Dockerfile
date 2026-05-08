FROM python:3.9-slim

# Install system dependencies for Prophet and others
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose ports
EXPOSE 8000
EXPOSE 8501

# Command to run the application
CMD ["./start.sh"]
