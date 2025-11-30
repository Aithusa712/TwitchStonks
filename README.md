# Twitch Stonks

A minimal real-time demo that turns a Twitch chat keyword into a live “stock price.” The stack includes FastAPI, MongoDB, and a Vite + React frontend, all runnable with Docker Compose.

## Prerequisites
- Docker and Docker Compose

## Setup
1. Copy the example environment file and fill in your Twitch credentials:
   ```bash
   cp .env.example .env
   ```
   Update `TWITCH_BOT_USERNAME`, `TWITCH_OAUTH_TOKEN` (format `oauth:xxxx`), and `TWITCH_CHANNEL`.

2. Start the stack:
   ```bash
   docker compose up --build
   ```

## Access
- Frontend: http://localhost:5173
- Backend: http://localhost:8000 (health at `/health`, history at `/history`, WebSocket at `/ws`)
- MongoDB: exposed on port 27017 (data persisted to `mongo_data` volume)

## How it works
- A Twitch IRC client listens to `irc.chat.twitch.tv` for chat messages in the configured channel.
- Every `TICK_INTERVAL_SECONDS` (default 2s), keyword hits are converted into a price change and appended to the `price_ticks` collection in MongoDB.
- New ticks are broadcast to all connected WebSocket clients so the chart updates instantly.

## Notes
- The app is read-only with Twitch chat; listening to public channels does not require channel owner action beyond valid credentials.
- Price changes are a simple demo formula; adjust `stonks_state.py` if you want different behavior.
