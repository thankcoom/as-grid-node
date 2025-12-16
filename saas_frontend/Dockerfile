# Stage 1: Build
FROM node:18-alpine as builder
WORKDIR /app
COPY package.json ./
# Create a dummy package-lock.json if not exists to avoid npm install errors, 
# though in real repo it should exist. npm install will generate it.
RUN npm install
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Add nginx config for React Router if needed (try_files $uri /index.html)
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
