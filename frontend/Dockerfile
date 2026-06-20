FROM oven/bun:1 AS base

WORKDIR /app

# Install dependencies
COPY package.json bun.lock bunfig.toml ./
RUN bun install --frozen-lockfile

# Copy source
COPY . .

# Vite env vars are baked at build time
ARG VITE_API_URL=http://localhost:8080
ARG VITE_WS_URL=ws://localhost:8080/ws
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL

# Build the app
RUN bun run build

EXPOSE 3000

CMD ["bunx", "vite", "preview", "--host", "0.0.0.0", "--port", "3000"]
