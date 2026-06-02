# Frontend (sadify-web) image for Cloud Run -- Next.js 16 standalone.
# Deploy: gcloud run deploy sadify-web --source apps/web --region asia-southeast1
#
# NEXT_PUBLIC_* are BUILD-TIME baked, so they are passed as --build-arg and the
# backend URL must already exist when this image is built.
FROM node:22-slim AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG NEXT_PUBLIC_SADIFY_API_BASE_URL
ARG NEXT_PUBLIC_FIREBASE_API_KEY
ARG NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN
ARG NEXT_PUBLIC_FIREBASE_PROJECT_ID
ARG NEXT_PUBLIC_FIREBASE_APP_ID
ARG NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID
ENV NEXT_PUBLIC_SADIFY_API_BASE_URL=$NEXT_PUBLIC_SADIFY_API_BASE_URL \
    NEXT_PUBLIC_FIREBASE_API_KEY=$NEXT_PUBLIC_FIREBASE_API_KEY \
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=$NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN \
    NEXT_PUBLIC_FIREBASE_PROJECT_ID=$NEXT_PUBLIC_FIREBASE_PROJECT_ID \
    NEXT_PUBLIC_FIREBASE_APP_ID=$NEXT_PUBLIC_FIREBASE_APP_ID \
    NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_OAUTH_CLIENT_ID

# Runs next build + prepare:standalone (copies static/ and public/ into the
# standalone tree so it is self-contained).
RUN npm run build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0

# The standalone output is self-contained (server.js + nested .next/static +
# public after prepare:standalone).
COPY --from=build /app/.next/standalone ./

# Cloud Run injects PORT; Next standalone server.js honours process.env.PORT.
CMD ["sh", "-c", "exec node server.js"]
