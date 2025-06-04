# Dockerfile for Agentic Search Application

# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for Selenium and Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    # Install Chrome dependencies
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

# Download and install Google Chrome (needed for chromedriver)
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -
RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
RUN apt-get update && apt-get install -y google-chrome-stable

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY scraper.py .
COPY llm_evaluator.py .
# Add main orchestrator script later if created
# COPY main.py .

# Define the command to run the application (assuming a main script exists)
# Replace 'main.py' with your actual entry point script
# For now, we can just run the evaluator test as an example
CMD ["python", "llm_evaluator.py"]

# Note: This Dockerfile assumes webdriver-manager is used or chromedriver is
# installed separately and its path is handled within the scraper script.
# If not using webdriver-manager, you would need to download and install
# the correct version of chromedriver here and ensure it's in the PATH.

