# RM Real Time Intelligence

An AI-powered assistant for Relationship Managers in wealth management. RM Compass listens to client calls in real time, understands what's being discussed, and surfaces relevant data — portfolio positions, market movements, news — exactly when the RM needs it.

## What it does

**During a call:**
- Transcribes the conversation live
- Detects topics as they come up (e.g. "client is asking about gold exposure")
- Instantly retrieves relevant portfolio data, trades, and market context
- Displays everything in a clean dashboard the RM can glance at

**After a call:**
- Generates a structured summary with key takeaways
- Tracks client sentiment throughout the conversation
- Flags potential risk-profile shifts
- Suggests follow-up actions

## Why it matters

Relationship managers juggle dozens of client relationships, each with unique portfolios and preferences. During a call, they often need to pull up data from multiple systems — portfolio positions, recent trades, market news — while maintaining a natural conversation. RM Compass eliminates that context-switching by proactively surfacing the right information at the right moment.

## How it works

The system has two parts:

- **Backend** — an AI pipeline that processes speech, segments it into meaningful concepts, and queries the client's data in real time
- **Frontend** — a web dashboard that displays the live transcript, detected concepts, and retrieved data side by side

## Running the project

You need [Docker](https://docs.docker.com/get-docker/) installed.

```bash
# 1. Set up your environment
cp .env.example .env
# Open .env and paste your OpenAI API key

# 2. Start everything
docker-compose up --build
```

Once running:
- Open http://localhost:8000 for the dashboard
- The backend API runs at http://localhost:8080

### Running without Docker

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

**Frontend:**
```bash
cd frontend
bun install
bun run dev
```

## Configuration

The only required setting is your OpenAI API key in the `.env` file. See `.env.example` for optional model overrides.

## Project structure

```
.
├── backend/          # AI pipeline and API server (Python)
├── frontend/         # Web dashboard (React)
├── docker-compose.yaml
└── .env.example      # Environment template
```

---

Built at Swiss Hacks 2026.
