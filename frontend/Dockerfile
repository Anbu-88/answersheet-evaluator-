# Use Nginx to serve the static content
FROM nginx:alpine

# Copy the static files to the Nginx public directory
COPY . /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
