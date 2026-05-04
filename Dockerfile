# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install only server-side runtime deps (Flask + YAML).
# Skipping the full Pipfile because pystray + Pillow pull macOS-only
# pyobjc-core via the macOS-generated Pipfile.lock; the menu bar tray is
# desktop-only and not used inside the container.
RUN pip install --no-cache-dir \
        flask \
        pyyaml

# Copy the rest of the application code
COPY . /app/

# Ensure the repositories directory exists inside the image
RUN mkdir -p /app/scanner/repositories

EXPOSE 5000

ENV FLASK_RUN_HOST=0.0.0.0

# Root app.py delegates to the scanner package
CMD ["python", "app.py"]
