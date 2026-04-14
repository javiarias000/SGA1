# Use a stable base image
FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary dependencies
RUN apt-get update && apt-get install -y \
    bash \
    curl \
    git \
    unzip \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Set up a working directory for Flutter SDK installation
WORKDIR /usr/local

# Download and install Flutter SDK as root
ENV FLUTTER_SDK_URL="https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.38.7-stable.tar.xz"
RUN wget -qO flutter-sdk.tar.xz "${FLUTTER_SDK_URL}" && \
    tar -xf flutter-sdk.tar.xz && \
    rm flutter-sdk.tar.xz

# Add Flutter to the PATH globally (for any user)
ENV PATH="/usr/local/flutter/bin:${PATH}"

# Create a non-root user
RUN useradd -ms /bin/bash -u 1000 user

# Change ownership of the Flutter SDK to the non-root user
RUN chown -R user:user /usr/local/flutter

# Switch to the non-root user for subsequent commands
USER user
WORKDIR /app # Set the working directory for the user

# Run flutter commands as the non-root user
RUN flutter precache
RUN flutter doctor

# Keep the container running
CMD ["tail", "-f", "/dev/null"]