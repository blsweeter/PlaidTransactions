FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install --prefer-offline --no-audit --no-fund

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]