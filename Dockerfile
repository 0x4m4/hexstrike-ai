# Stage 1: Build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit
COPY . .
RUN npm run build:prod

# Stage 2: Serve
FROM nginx:alpine
RUN addgroup -g 1001 -S appuser && adduser -u 1001 -S appuser -G appuser
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
RUN chown -R appuser:appuser /usr/share/nginx/html /var/cache/nginx /var/log/nginx /run
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3000/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
