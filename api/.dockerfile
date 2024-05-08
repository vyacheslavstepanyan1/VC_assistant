# Use the specific Python version from the Docker Hub
FROM python:3.12.3-alpine3.18

RUN apk add --no-cache gcc musl-dev linux-headers

# Set the working directory in the container
WORKDIR /api

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the dependencies specified in the requirements.txt file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container, excluding paths in .dockerignore
COPY . .

# Make port 8000 available for the app
EXPOSE 8000

ENV PYTHONUNBUFFERED=1

# Define the command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]