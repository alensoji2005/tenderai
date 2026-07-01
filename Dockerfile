# Use Python 3.10 slim image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies, including those required for Google Chrome and Selenium
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libnss3 \
    libxss1 \
    libasound2 \
    fonts-liberation \
    libgbm1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Generate Prisma client
RUN prisma generate

# Expose port (Render sets the PORT environment variable automatically)
EXPOSE 8000

# Start command
# We use Prisma db push (or migrate deploy) and then start the Uvicorn server
CMD prisma db push --accept-data-loss && uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
