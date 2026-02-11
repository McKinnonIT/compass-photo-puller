# Compass Photo Retrieval – fetch and download staff/student photos
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (compass_photo package, run script, shim)
COPY compass_photo/ ./compass_photo/
COPY compassphoto.py run.py ./

# PHOTOS_DIR is set at runtime; default /app/photos when running in compose
# Run the photo fetch + download
CMD ["python", "run.py"]
