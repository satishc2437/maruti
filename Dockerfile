# Use Python 3.13 official image which is more reliable
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    vim \
    nano \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install UV package manager (modern Python package manager)
RUN python -m pip install --upgrade pip && \
    python -m pip install uv

# Copy project configuration first for better caching
COPY pyproject.toml uv.lock* ./
COPY pdf-reader/pyproject.toml ./pdf-reader/
COPY onenote-reader/pyproject.toml ./onenote-reader/
COPY xlsx-reader/pyproject.toml ./xlsx-reader/

# Install project dependencies using UV (dependencies only first)
RUN uv sync --dev --no-editable

# Copy project files
COPY . .

# Install the project in development mode
RUN uv sync --dev

# Create a development info script
RUN echo '#!/bin/bash' > /app/setup-dev.sh && \
    echo 'echo "Maruti Development Environment Ready!"' >> /app/setup-dev.sh && \
    echo 'echo "Available commands:"' >> /app/setup-dev.sh && \
    echo 'echo "  uv run pdf-reader     - Run PDF reader MCP server"' >> /app/setup-dev.sh && \
    echo 'echo "  uv run xlsx-reader    - Run XLSX reader MCP server"' >> /app/setup-dev.sh && \
    echo 'echo "  uv run onenote-reader - Run OneNote reader MCP server"' >> /app/setup-dev.sh && \
    echo 'echo "  uv add <package>      - Add new dependency"' >> /app/setup-dev.sh && \
    echo 'echo "  uv run pytest        - Run tests"' >> /app/setup-dev.sh && \
    chmod +x /app/setup-dev.sh

# Expose common development ports
EXPOSE 8000 8080 3000 5000

# Set environment variables for development
ENV PYTHONPATH=/app
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

# Default command
CMD ["/bin/bash", "-c", "/app/setup-dev.sh && echo 'Container ready for development. Use docker exec to connect.' && sleep infinity"]