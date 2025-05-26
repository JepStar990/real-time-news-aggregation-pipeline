# Dockerfile

FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure gunicorn is installed
RUN pip install gunicorn

# Copy the application code
COPY ./rss_feeder /app/rss_feeder

# Set environment variables
ENV PYTHONPATH=/app/rss_feeder

# Expose the application port
EXPOSE 8000

# Ensure the config file is copied
COPY ./rss_feeder/logging.conf /app/rss_feeder/logging.co

# Run directly without intermediate shell
#CMD ["python", "-m", "rss_feeder.__main__"]
#CMD ["sh", "-c", "python -m rss_feeder.__main__ --log-level debug"]
CMD ["uvicorn", "rss_feeder.__main__:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]
