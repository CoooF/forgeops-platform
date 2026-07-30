FROM node:24.14.0-bookworm-slim

WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
RUN pnpm --filter @forgeops/web build

USER node
EXPOSE 4173
CMD ["pnpm", "--filter", "@forgeops/web", "exec", "vite", "preview", "--host", "0.0.0.0", "--port", "4173"]
