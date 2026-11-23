# Frontend image: Vite build -> Nginx static hosting + /api reverse proxy
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci --registry=https://registry.npmmirror.com
COPY . .
ARG VITE_BAIDU_MAP_AK=
ENV VITE_BAIDU_MAP_AK=$VITE_BAIDU_MAP_AK
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
