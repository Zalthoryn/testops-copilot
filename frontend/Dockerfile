FROM node:20-alpine AS builder
WORKDIR /app

# Build-time API URL for the frontend -> backend calls
ARG VITE_API_BASE=http://localhost:8000/api
ENV VITE_API_BASE=${VITE_API_BASE}

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
RUN npm install -g serve
COPY --from=builder /app/dist ./dist
EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "3000"]
