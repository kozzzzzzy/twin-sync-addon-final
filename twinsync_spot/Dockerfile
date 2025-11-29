ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    ffmpeg

# Set working directory
WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Copy run script
COPY run.sh /run.sh
RUN chmod a+x /run.sh

# Create data directory
RUN mkdir -p /data

# Labels
LABEL \
    io.hass.name="TwinSync Spot" \
    io.hass.description="Does this match YOUR definition?" \
    io.hass.type="addon"

# Use CMD to run directly (bypasses s6 service management)
CMD ["/run.sh"]
