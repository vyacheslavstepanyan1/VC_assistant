# Use an official Node.js runtime as the base image
FROM node:20.12.2-alpine3.18

# Set the working directory in the container
WORKDIR /client

# Copy package.json and package-lock.json (if available)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the remaining application code
COPY . .

# Build the React app
RUN npm run build

# Expose the port on which your React app will run (usually 3000)
EXPOSE 3000

# Start the React app
CMD ["npm", "start"]
