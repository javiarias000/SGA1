# Build stage
FROM ubuntu:22.04 as builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash curl git unzip wget xz-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local

# Install Flutter SDK
ENV FLUTTER_SDK_URL="https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.38.7-stable.tar.xz"
RUN wget -qO flutter-sdk.tar.xz "${FLUTTER_SDK_URL}" && \
    tar -xf flutter-sdk.tar.xz && \
    rm flutter-sdk.tar.xz

ENV PATH="/usr/local/flutter/bin:${PATH}"

# Fix git ownership for Flutter SDK
RUN git config --global --add safe.directory /usr/local/flutter

# Copy app source and build
WORKDIR /app
COPY mobile_app .
RUN flutter build web

# Production stage
FROM nginx:alpine

# Copy built Flutter web artifacts to Nginx html directory
COPY --from=builder /app/build/web /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
