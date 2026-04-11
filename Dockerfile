# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy scanner dependencies first (layer-cache friendly)
COPY scanner/Pipfile scanner/Pipfile.lock ./

# Install pipenv and project dependencies system-wide
RUN pip install --no-cache-dir pipenv && \
    pipenv install --system --deploy

# Copy the rest of the application code
COPY . /app/

# Ensure the repositories directory exists inside the image
RUN mkdir -p /app/scanner/repositories

EXPOSE 5000

ENV FLASK_RUN_HOST=0.0.0.0

# Root app.py delegates to the scanner package
CMD ["python", "app.py"]
