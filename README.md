# AI Support Ticket Automation

Paste a customer support ticket and the app will classify it, analyse the case,
decide the next step and draft a reply. Built with FastAPI, LangChain and React.

## Features

- Ticket triage (category, priority, language)
- Category-specific case analysis
- Resolution decision and a ready-to-send customer reply
- Dashboard with stats, search, filters and ticket details
- Batch upload from a JSON file
- Dark and light theme

## Run with Docker

1. Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY`.
2. Start everything:

       docker compose up --build

3. Open http://localhost:3000 (API docs: http://localhost:8000/docs).

Useful commands:

    docker compose logs -f backend   # follow backend logs
    docker compose down              # stop, keep the database
    docker compose down -v           # stop and delete the database

## Run locally without Docker

Backend (Python 3.11 or 3.12):

    cd backend
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Frontend (Node 18 or newer):

    cd frontend
    npm install
    npm run dev

## Project structure

    backend/    FastAPI app, LangChain chains, prompts, SQLite storage
    frontend/   React + Vite + Tailwind app, served by nginx in Docker
    sample_data/support_tickets.json   example tickets for batch upload

## API

    GET    /api/health
    POST   /api/tickets
    POST   /api/tickets/batch
    GET    /api/tickets
    GET    /api/tickets/{ticket_id}
    DELETE /api/tickets/{ticket_id}
    GET    /api/stats
