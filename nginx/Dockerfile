# Multi-stage build for FHIR Nginx Frontend
FROM node:18-alpine AS frontend-builder

# Set working directory
WORKDIR /app

# Copy static assets
COPY fastapi-app/static ./static
COPY fastapi-app/templates ./templates

# Simply copy static assets (skip optimization for now)
RUN echo "Assets copied successfully"

# Production stage
FROM nginx:1.24-alpine

# Install curl for health checks
RUN apk add --no-cache curl

# Remove default nginx website
RUN rm -rf /usr/share/nginx/html/*

# Copy nginx configuration
COPY ./nginx/nginx.conf /etc/nginx/nginx.conf

# Copy optimized static assets from builder stage
COPY --from=frontend-builder /app/static /usr/share/nginx/html/static

# Create directories and set permissions
RUN mkdir -p /var/cache/nginx /var/log/nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx /usr/share/nginx/html /var/log/nginx

# Create simple index.html
RUN echo '<!DOCTYPE html><html><head><title>FHIR System</title><meta charset="utf-8"><style>body{font-family:sans-serif;text-align:center;padding:50px;background:#f5f5f5}h1{color:#333}</style></head><body><h1>FHIR Distributed System</h1><p>Frontend Loading...</p></body></html>' > /usr/share/nginx/html/index.html

# Health check script
RUN echo '#!/bin/sh\ncurl -f http://localhost/health || exit 1' > /usr/local/bin/health-check.sh && \
    chmod +x /usr/local/bin/health-check.sh

# Switch to non-root user
USER nginx

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/health-check.sh

# Start nginx
CMD ["nginx", "-g", "daemon off;"]