FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir -e "."

# Create non-root user
RUN useradd -m -u 1000 orkit && chown -R orkit:orkit /app
USER orkit

# Expose port (if needed for API mode)
EXPOSE 8000

# Default command
CMD ["orkit", "--help"]
