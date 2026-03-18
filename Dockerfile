FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Pillow and video processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create necessary directories
RUN mkdir -p downloads data logs

# Run the bot
CMD ["python", "-m", "bot.main"]
