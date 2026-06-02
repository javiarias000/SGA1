# ─── Build stage ─────────────────────────────────────────────────────────────
FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    bash curl git unzip wget xz-utils ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local

# Install Flutter SDK (stable channel, latest available)
# Uses the git-based install so it always picks latest stable
RUN git clone https://github.com/flutter/flutter.git --branch stable --depth 1 flutter

ENV PATH="/usr/local/flutter/bin:/usr/local/flutter/bin/cache/dart-sdk/bin:${PATH}"

RUN git config --global --add safe.directory /usr/local/flutter

# Pre-cache Flutter web artifacts
RUN flutter precache --web

# ─── App build ───────────────────────────────────────────────────────────────
WORKDIR /app
COPY mobile_app/pubspec.yaml mobile_app/pubspec.lock ./
RUN flutter pub get

COPY mobile_app .

# API_URL build-arg — defaults to connecting to the backend Docker service
ARG API_URL=http://backend:8000
RUN flutter build web --dart-define=API_URL=${API_URL} --release

# ─── Production stage ─────────────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /app/build/web /usr/share/nginx/html

# nginx config for SPA routing (all paths return index.html)
RUN printf 'server {\n\
    listen 80;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
