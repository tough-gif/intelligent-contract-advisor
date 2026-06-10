# Use Python 3.12 slim image
FROM python:3.12-slim

# Install uv for fast dependency installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy project configuration files
COPY pyproject.toml uv.lock ./

# Copy application code
COPY contract_advisor/ ./contract_advisor/
COPY README.md ./

# Install dependencies (system-wide for simplicity in container)
RUN uv pip install --system .

# Copy the Gradio app script
COPY gradio_app.py ./

# Expose port 8080 (Cloud Run default)
EXPOSE 8080

# Run the app
CMD ["python", "gradio_app.py"]
