FROM python:3.11-slim

WORKDIR /workspace

# Install system dependencies (OpenCV requires libgl1 and libglib-2.0 in headless containers)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Initialize DB during build to verify sqlite connectivity
RUN python -c "from app.db import init_db; init_db()"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
