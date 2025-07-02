# Stage 1: Generate SSL certificate
FROM alpine:3.18 as cert-generator
RUN apk add --no-cache openssl
RUN mkdir -p /etc/nginx/ssl
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/nginx-selfsigned.key \
    -out /etc/nginx/ssl/nginx-selfsigned.crt \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,DNS:127.0.0.1"

# Stage 2: Build Nginx with SSL
FROM nginx:1.25-alpine

# Install OpenSSL
RUN apk add --no-cache openssl

# Create necessary directories with correct permissions
RUN mkdir -p /var/log/nginx \
    && mkdir -p /var/cache/nginx \
    && mkdir -p /etc/nginx/ssl \
    && mkdir -p /app/staticfiles \
    && mkdir -p /app/media \
    && touch /var/log/nginx/access.log \
    && touch /var/log/nginx/error.log \
    && chown -R nginx:nginx /var/log/nginx /var/cache/nginx /etc/nginx /app \
    && chmod -R 755 /var/log/nginx /etc/nginx /app

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy SSL certificates from cert-generator
COPY --from=cert-generator /etc/nginx/ssl/ /etc/nginx/ssl/

# Set proper permissions for SSL certificates
RUN chmod 600 /etc/nginx/ssl/nginx-selfsigned.* \
    && chown nginx:nginx /etc/nginx/ssl/nginx-selfsigned.*

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Set the working directory
WORKDIR /app

# Expose ports
EXPOSE 80 443

# Start Nginx as root (needed for ports < 1024)
# The nginx process inside the container will drop privileges to nginx user
CMD ["nginx", "-g", "daemon off;"]
