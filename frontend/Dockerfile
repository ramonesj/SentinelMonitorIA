FROM node:24-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd

WORKDIR /app

COPY --chown=node:node frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY --chown=node:node frontend/ .
COPY --chown=node:node Imagenes /Imagenes
RUN chown -R node:node /app

ENV HOST=0.0.0.0
ENV NODE_ENV=development

USER node
EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
