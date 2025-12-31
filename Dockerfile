# Use a lightweight Python base image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose FastAPI port
EXPOSE 80

# Run FastAPI app with uvicorn
CMD ["uvicorn", "burrow.app.main:app", "--host", "0.0.0.0", "--port", "80"]
