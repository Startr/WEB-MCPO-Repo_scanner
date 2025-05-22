# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy Pipfile and Pipfile.lock
COPY Pipfile Pipfile.lock /app/

# Install pipenv and then project dependencies
RUN pip install pipenv && \
    pipenv install --system --deploy --ignore-pipfile

# Copy the rest of the application code into the container
COPY . /app/

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP app.py
ENV FLASK_RUN_HOST 0.0.0.0

# Run app.py when the container launches
CMD ["python", "app.py"]
