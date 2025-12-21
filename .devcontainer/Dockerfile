# Dev Container Dockerfile for Maruti Project
FROM python:3.14-slim

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
COPY mcp-tools/pdf-reader/pyproject.toml ./mcp-tools/pdf-reader/
COPY mcp-tools/onenote-reader/pyproject.toml ./mcp-tools/onenote-reader/
COPY mcp-tools/xlsx-reader/pyproject.toml ./mcp-tools/xlsx-reader/
COPY mcp-tools/agent-memory/pyproject.toml ./mcp-tools/agent-memory/

# Create virtual environment and install dependencies
RUN uv sync --dev --no-editable

# Copy the rest of the project
COPY . .

# Install project in editable mode
RUN uv sync --dev

# Auto-discover and install all MCP servers in editable mode
RUN for dir in mcp-tools/*/; do \
        if [ -f "${dir}pyproject.toml" ]; then \
            if grep -q "mcp\|Model Context Protocol" "${dir}pyproject.toml" 2>/dev/null; then \
                echo "Installing MCP server: ${dir%/}" && \
                cd "$dir" && uv pip install -e . && cd - >/dev/null; \
            fi; \
        fi; \
    done

# Create a user for development (optional, but good practice)
RUN useradd -m -s /bin/bash devuser && \
    chown -R devuser:devuser /app

# Keep container running
CMD ["sleep", "infinity"]
