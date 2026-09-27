# ---- deps ----
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- builder ----
FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* vars are inlined into the browser bundle at build time, so
# they must be supplied as build args, not just runtime env — see next.config.ts
# (output: "standalone") and the Next.js self-hosting docs.
ARG NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
# CLERK_SECRET_KEY is server-only and read at runtime (see the "runner" stage
# below) — but the build itself still needs *a* validly-formatted key present
# or Clerk's build-time checks fail; it is not baked into the output.
ENV CLERK_SECRET_KEY=sk_test_00000000000000000000000000000000000000000000

RUN npm run build

# ---- runner ----
FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

RUN useradd --create-home --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

# CLERK_SECRET_KEY must be supplied as a real runtime env var (docker-compose
# `environment:` or equivalent) — the build-time placeholder above is not used
# at request time.
CMD ["node", "server.js"]
