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

# Copy s6-overlay service definitions
COPY rootfs/ /

# Make service scripts executable
RUN chmod a+x /etc/services.d/twinsync/run \
    && chmod a+x /etc/services.d/twinsync/finish

# Create data directory
RUN mkdir -p /data

# Labels
LABEL \
    io.hass.name="TwinSync Spot" \
    io.hass.description="Does this match YOUR definition?" \
    io.hass.type="addon"
