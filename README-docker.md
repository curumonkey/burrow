#!/usr/bin/env bash
# ============================================================================
# Burrow Project – Docker end-to-end walkthrough (commands + explanations)
# Run or read this as a reference. Lines starting with '#' are explanations.
# ============================================================================

# ----------------------------------------------------------------------------
# 1) Project structure (context)
# ----------------------------------------------------------------------------
# We dockerized a FastAPI-style project with this tree (simplified):
# .
# ├── burrow
# │   └── app
# │       ├── main.py           # FastAPI entrypoint
# │       └── api/v1/...        # Your endpoints (hello.py, auth.py, etc.)
# ├── requirements.txt          # Python dependencies
# └── README.md

# ----------------------------------------------------------------------------
# 2) Create Dockerfile at project root (Biome/burrow-project)
# ----------------------------------------------------------------------------
# This builds a Python 3.11 slim image, installs deps, and runs uvicorn.
cat > Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system deps if needed (uncomment and adjust as necessary)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose FastAPI port
EXPOSE 80

# Run the app (adjust module path if needed)
CMD ["uvicorn", "burrow.app.main:app", "--host", "0.0.0.0", "--port", "80"]
EOF

# ----------------------------------------------------------------------------
# 3) Build the image
# ----------------------------------------------------------------------------
# Builds the 'burrow-api' image from the current directory's Dockerfile.
sudo docker build -t burrow-api .

# ----------------------------------------------------------------------------
# 4) Run the container
# ----------------------------------------------------------------------------
# Map host port (e.g., 8000) to container port 80 and name it 'burrow-container'.
# If the port is in use, change 8000 to another free port (e.g., 8001).
sudo docker run -d -p 8000:80 --name burrow-container burrow-api

# ----------------------------------------------------------------------------
# 5) Diagnose port conflicts
# ----------------------------------------------------------------------------
# If you see "port is already allocated", check what's listening:
sudo ss -tuln | grep -E ':(8000|8080|15611|5432|6379|53|631)\b'  # Adjust ports as needed

# See which process is using a specific port:
sudo lsof -i:8000

# If a Docker container holds the port, list and stop it:
sudo docker ps
# Example: stop/remove the conflicting container
sudo docker stop burrow-container || true
sudo docker rm burrow-container || true

# Then re-run on a free port:
sudo docker run -d -p 8001:80 --name burrow-container burrow-api

# ----------------------------------------------------------------------------
# 6) Container + image housekeeping
# ----------------------------------------------------------------------------
# List running containers:
sudo docker ps

# List all containers, including stopped:
sudo docker ps -a

# Stop/start/remove a container:
sudo docker stop burrow-container
sudo docker start burrow-container
sudo docker rm burrow-container

# Prune all stopped containers (careful – deletes all stopped):
sudo docker container prune -f

# List images:
sudo docker images

# Remove an image (if not used by a container):
# sudo docker rmi burrow-api

# ----------------------------------------------------------------------------
# 7) Save image to a tar and copy to USB
# ----------------------------------------------------------------------------
# Save the image to a portable tar file:
sudo docker save -o burrow-api.tar burrow-api

# Find your USB mount (usually /media/<username>/<LABEL>):
lsblk
df -h

# Copy to USB (replace <username> and <LABEL> accordingly):
sudo cp burrow-api.tar /media/solo-monkey/7000-8000/dockerized-projects/

# Safely unmount when done:
sudo umount /media/solo-monkey/7000-8000

# ----------------------------------------------------------------------------
# 8) Load the image on another computer and run
# ----------------------------------------------------------------------------
# Copy tar from USB to local (optional):
cp /media/<username>/<LABEL>/burrow-api.tar ~/

# Load into Docker:
sudo docker load -i ~/burrow-api.tar

# Run the container on that machine:
sudo docker run -d -p 8000:80 --name burrow-container burrow-api

# If name conflict occurs (container with same name already exists):
sudo docker ps -a
sudo docker stop burrow-container || true
sudo docker rm burrow-container || true
sudo docker run -d -p 8000:80 --name burrow-container burrow-api
# Or use a new name:
sudo docker run -d -p 8000:80 --name burrow-container-v2 burrow-api

# ----------------------------------------------------------------------------
# 9) Development tips
# ----------------------------------------------------------------------------
# - If you update requirements.txt, rebuild the image:
sudo docker build -t burrow-api .
# - Tag versions to track builds:
sudo docker tag burrow-api burrow-api:v1
# - Run a specific tag:
sudo docker run -d -p 8000:80 --name burrow-container burrow-api:v1
# - Mount source code for live editing (dev only):
sudo docker run -d -p 8000:80 -v "$PWD":/app --name burrow-dev burrow-api
#   (If your app auto-reloads, add --reload to uvicorn in CMD or override:
#    sudo docker run -d -p 8000:80 -v "$PWD":/app burrow-api \
#      uvicorn burrow.app.main:app --host 0.0.0.0 --port 80 --reload)

# ----------------------------------------------------------------------------
# 10) Troubleshooting quick commands
# ----------------------------------------------------------------------------
# Look at container logs:
sudo docker logs -f burrow-container

# Enter a shell inside the running container:
sudo docker exec -it burrow-container /bin/sh
# Verify Python packages inside the container:
sudo docker exec -it burrow-container pip list

# ----------------------------------------------------------------------------
# End of walkthrough
# ----------------------------------------------------------------------------
