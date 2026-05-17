FROM python:3.11-slim

# Install system dependencies and Node.js
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv for Python package management natively
RUN pip install uv

# HuggingFace Spaces requires non-root user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy all project files into the container securely
COPY --chown=user . $HOME/app/

# Create python structure under backend
RUN cd backend && uv venv && uv pip install -r requirements.txt

# Ensure start script is executable
RUN chmod +x start.sh

# HuggingFace natively routes to port 7860
EXPOSE 7860

CMD ["./start.sh"]
