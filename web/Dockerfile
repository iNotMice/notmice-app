# Production edge: build the Vite app, then serve it from nginx.
# Build context is the repository root. VITE_API_BASE_URL stays empty so
# the browser calls /api on the same origin as the site.

FROM node:22-bookworm-slim AS build

WORKDIR /src

ARG VITE_API_BASE_URL=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json .npmrc ./
RUN npm ci

COPY index.html vite.config.ts tsconfig.json ./
COPY public ./public
COPY src ./src

RUN npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache apache2-utils

COPY proxy/nginx.prod.conf /etc/nginx/conf.d/default.conf
COPY proxy/40-docs-basic-auth.sh /docker-entrypoint.d/40-docs-basic-auth.sh
RUN chmod 755 /docker-entrypoint.d/40-docs-basic-auth.sh

COPY --from=build /src/dist /usr/share/nginx/html

EXPOSE 80
