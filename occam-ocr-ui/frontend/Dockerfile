# build environment
# source: https://mherman.org/blog/dockerizing-a-react-app/
FROM node:16.17.0-alpine AS build
WORKDIR /frontend
ENV PATH=/frontend/node_modules/.bin:$PATH
COPY package.json ./
COPY package-lock.json ./
RUN NODE_OPTIONS=--max_old_space_size=1024 npm ci

RUN NODE_OPTIONS=--max_old_space_size=1024 npm install react-scripts@5.0.1 -g
RUN NODE_OPTIONS=--max_old_space_size=1024 npm install sass -g
COPY . ./
RUN NODE_OPTIONS=--max_old_space_size=1024 npm run build

# production environment
FROM nginx:stable-alpine
COPY --from=build /frontend/build /usr/share/nginx/html
# new
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80

# Copy .env file and shell script to container
WORKDIR /usr/share/nginx/html
COPY ./env.sh .
COPY ./.env.sample ./.env.local

# Add bash
RUN apk add --no-cache bash

# Make our shell script executable
RUN chmod +x env.sh \
	&& chmod -R a+rX /usr/share/nginx/html

CMD ["/bin/bash", "-c", "/usr/share/nginx/html/env.sh && nginx -g \"daemon off;\""]
