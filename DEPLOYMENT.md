# Deployment Guide


This document describes how to deploy the Twitch Stonks application to Azure using Static Web Apps for the frontend, Azure Web App for Containers for the backend, Docker Hub as the registry, and MongoDB Atlas for the database.

## Environment Variables

### Backend (FastAPI)
| Variable | Description |
| --- | --- |
| `TWITCH_BOT_USERNAME` | Username of the Twitch bot account. |
| `TWITCH_OAUTH_TOKEN` | OAuth token for the bot (format `oauth:...`). |
| `TWITCH_CHANNEL` | Twitch channel to monitor. |
| `TWITCH_CLIENT_ID` | Twitch application client ID. |
| `TWITCH_CLIENT_SECRET` | Twitch application client secret. |
| `STONKS_UP_KEYWORD` | Keyword representing an "up" vote in chat. |
| `STONKS_DOWN_KEYWORD` | Keyword representing a "down" vote in chat. |
| `MONGO_URI` | MongoDB Atlas connection string (e.g. `mongodb+srv://<user>:<password>@cluster0.example.mongodb.net/?retryWrites=true&w=majority`). |
| `MONGO_DB_NAME` | Database name (default: `stonksdb`). |
| `ALLOWED_ORIGINS` | Comma-separated list of origins allowed for CORS (include your SWA URL). |
| `TICK_INTERVAL_MINUTES` | Minutes between price ticks (default: `30`). |
| `INITIAL_PRICE` | Starting price value. |

### Frontend (Vite + React)
| Variable | Description |
| --- | --- |
| `VITE_API_BASE_URL` | Base URL for the backend API (e.g. `https://<backend>.azurewebsites.net`). |
| `VITE_TWITCH_CHANNEL` | Optional: default Twitch channel name to display. |

## GitHub Secrets

Configure the following secrets in the repository settings:

- `AZURE_STATIC_WEB_APPS_API_TOKEN` – Deployment token for Azure Static Web Apps.
- `DOCKERHUB_USERNAME` – Docker Hub username used for pushing backend images.
- `DOCKERHUB_TOKEN` – Docker Hub access token/password.
- `AZURE_WEBAPP_PUBLISH_PROFILE` – Publish profile XML for the Azure Web App (recommended) or set Azure credentials environment variables instead.
- `VITE_API_BASE_URL` – Production API endpoint for building the frontend.

(Optional) Configure a repository variable `AZURE_WEBAPP_NAME` with the name of the Azure Web App resource; the backend workflow will use this value.

## Azure Configuration

### MongoDB Atlas
1. Create a free tier cluster and database user.
2. Allow access from Azure by whitelisting IP addresses (or set `0.0.0.0/0` temporarily for testing).
3. Obtain the SRV connection string and place it in the `MONGO_URI` setting.

### Azure Web App for Containers
1. Create a Web App configured for Docker Hub images.
2. Set the following application settings in the Azure portal (Configuration > Application settings):
   - All backend variables listed above (Twitch, MongoDB, CORS, etc.).
3. Enable WebSockets in "General Settings" for the Web App.
4. Optional: configure Health check to `/health`.

### Azure Static Web Apps
1. Create a Static Web App resource.
2. Note the production hostname (e.g. `https://<name>.azurestaticapps.net`) and add it to `ALLOWED_ORIGINS`.
3. Generate a deployment token and save it as `AZURE_STATIC_WEB_APPS_API_TOKEN` in GitHub secrets.

## Deployment Steps

1. Ensure `.env.example` is updated with your values; copy to `.env` for local testing if needed.
2. Push changes to the `prod` branch. The GitHub Actions workflows will:
   - Build and deploy the frontend to Static Web Apps.
   - Build a backend Docker image, push it to Docker Hub, and deploy it to Azure Web App for Containers.
3. Verify deployments:
   - Frontend served from the SWA URL.
   - Backend reachable at Azure Web App URL and `/health` returns `{"status": "ok"}`.
   - WebSocket endpoint `/ws` responds and streams updates.
   - MongoDB Atlas shows incoming data.

## GitHub Actions Overview

- `azure-swa-frontend.yml` builds the Vite app and deploys it to Static Web Apps. It expects `VITE_API_BASE_URL` and `AZURE_STATIC_WEB_APPS_API_TOKEN` secrets.
- `azure-webapp-backend.yml` builds the backend container, pushes it to Docker Hub, and deploys the image to the configured Azure Web App using `AZURE_WEBAPP_PUBLISH_PROFILE`, `DOCKERHUB_USERNAME`, and `DOCKERHUB_TOKEN` secrets.

## Notes
- Always use HTTPS endpoints in production for both API and WebSocket (automatically derived from `VITE_API_BASE_URL`).
- Keep secrets out of the repository and rotate them regularly.
- Update `ALLOWED_ORIGINS` when domains change to keep CORS restrictive.
