# Dev Container Dockerfile for Maruti Project
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    nano \
    build-essential \
    pkg-config \
    libssl-dev \
    libffi-dev \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --upgrade pip && pip install uv

# Set working directory
WORKDIR /app

# Copy project configuration files first for better caching
COPY pyproject.toml uv.lock* ./
COPY pdf-reader/pyproject.toml ./pdf-reader/
COPY onenote-reader/pyproject.toml ./onenote-reader/
COPY xlsx-reader/pyproject.toml ./xlsx-reader/

# Create virtual environment and install dependencies
RUN uv sync --dev --no-editable

# Copy the rest of the project
COPY . .

# Install project in editable mode
RUN uv sync --dev

# Create a user for development (optional, but good practice)
RUN useradd -m -s /bin/bash devuser && \
    chown -R devuser:devuser /app

# Keep container running
CMD ["sleep", "infinity"]