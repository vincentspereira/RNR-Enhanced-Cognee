# Use an official Node.js runtime as a parent image
FROM node:22.23.3-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402

# Set the working directory to /app
WORKDIR /app

# Copy package.json and package-lock.json to the working directory
COPY package.json package-lock.json ./

# Install any needed packages specified in package.json
RUN npm ci --ignore-scripts

# Copy the rest of the application code to the working directory
COPY src ./src
COPY public ./public
COPY next.config.mjs .
COPY postcss.config.mjs .
COPY tsconfig.json .
COPY types ./types
COPY eslint.config.mjs .
COPY security-backports ./security-backports
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run security:backport

# Build the app and run it
CMD ["npm", "run", "dev"]
