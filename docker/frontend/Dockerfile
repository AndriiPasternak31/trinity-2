FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies - use npm install instead of npm ci to handle optional deps better
# and explicitly install rollup ARM64 Alpine binary if needed
RUN npm install && \
    if [ "$(uname -m)" = "aarch64" ]; then \
        npm install --no-save @rollup/rollup-linux-arm64-musl || true; \
    fi

# Copy application code
COPY . .

# Expose port
EXPOSE 80

# Run the development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
