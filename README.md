# AI Voice Support Desk (AI Support Ticket Automation)

A customer calls, an AI voice agent answers from the company knowledge base, and every call is turned into a triaged support ticket with a drafted reply. Refunds and other money decisions are never made by the AI: they always go to a human.

Built for the Bolna Buildathon on top of my earlier AI Support Ticket Automation project.

> TechNova is a fictional company. The knowledge base in `backend/knowledge/` is a demo dataset, and the prices and policies in it are made up. Swap in real documents to use it for a real company.

**Live demo:** https://3-107-146-58.sslip.io/ (dashboard with processed tickets)
Some tickets in the demo dashboard were created from simulated call transcripts (see `backend/scripts/seed_demo_calls.py`); the others come from real test calls.

## What it does

**During the call**
1. The customer talks to a voice agent built on Bolna.
2. For product, billing and policy questions the agent calls `POST /api/voice/ask`.
3. The backend retrieves matching chunks from the knowledge base (embedding search), then writes a short spoken answer using only that context. If nothing relevant is found, it says it does not know instead of guessing.

**After the call**
1. Bolna sends the finished call to `POST /api/voice/webhook`.
2. A four-stage LangChain pipeline runs on the transcript: triage (category, priority, language), category-specific analysis, resolution decision, and a drafted customer reply. Every stage returns validated Pydantic output.
3. The ticket appears in the dashboard with a Voice badge and the call transcript.

## Architecture

```
Caller -> Bolna voice agent -> POST /api/voice/ask  -> RAG over knowledge base -> short answer
                            -> POST /api/voice/webhook (after the call)
                                      |
                                      v
                    LangChain pipeline (triage, analysis, resolution, reply)
                                      |
                                      v
                          SQLite -> FastAPI -> React dashboard
Production: Docker Compose (backend, Nginx-served frontend, Caddy for HTTPS) on AWS EC2
```

The slow part, the four-stage pipeline, runs after the call. During the call the agent only waits for one retrieval and one short LLM answer, because a phone line cannot afford long silences.

## How the Bolna agent is configured

- **Agent:** created in Bolna with a short system prompt, guardrails (never invent prices or policies, never claim to be human) and a conversation flow that sends every plan, billing, account or policy question to the knowledge base.
- **Custom function** `search_knowledge_base`: a POST to `/api/voice/ask` with one parameter, `query`, which the agent writes in clear English even when the caller speaks Hindi or Hinglish. The response contains `found`, `answer` and `sources`.
- **Webhook:** Bolna posts every call status update to `/api/voice/webhook`. Only a `completed` call that contains caller speech creates a ticket. The ticket ID is `CALL-` plus the first 8 characters of the call ID, so repeated deliveries of the same call do not create duplicates.
- **Authentication:** both the function and the webhook send a shared secret in the `X-Voice-Secret` header. Requests without it get a 401.

## Retrieval evaluation (internal)

I compared three retrieval modes on 50 labeled questions (25 close to the documents, 25 paraphrased or spoken-style) plus 13 questions the documents cannot answer. No LLM calls are involved in this table.

| Mode | Easy hit@1 | Hard hit@1 | Hard hit@3 | Hard MRR |
|------|-----------|-----------|-----------|----------|
| vector (used) | 96% | 80% | 96% | 0.873 |
| hybrid (vector + BM25) | 92% | 72% | 100% | 0.853 |
| rerank (hybrid + cross-encoder) | 92% | 80% | 96% | 0.880 |

On this small, cleanly structured knowledge base (77 chunks), hybrid search and reranking gave no measurable gain over plain vector search, so the demo keeps vector search. Differences of one or two questions are noise at this size. These numbers come from a synthetic dataset I wrote myself, so they say little about real-world accuracy.

Answer safety check: for the 13 unanswerable questions, retrieval alone stopped 7. The answer prompt refused the remaining 6, so the pipeline said it did not know on all 13. Three trap prompts (approve a refund, grant a lifetime plan, claim to be human) were also answered correctly. Run `python scripts/eval_answers.py` to reproduce.

## Performance

- **Answer endpoint:** median 2.35 s, p95 5.63 s (min 2.11 s, max 6.08 s) over 20 timed calls to `/api/voice/ask`, made from a laptop in India to the EC2 server in Sydney. This includes the network round trip and excludes Bolna's speech recognition and speech synthesis, so the delay a caller hears is longer. Reproduce with `python scripts/measure_latency.py <server url>`.
- **Ticket pipeline:** about 60 s per ticket on a free OpenRouter model, under 15 s per ticket with a fast paid model (read from the stored `processing_ms` field in my test runs, not a controlled benchmark).
- Twenty calls is a small sample, so treat the p95 as a rough guide.

## Safety rules

- Critical tickets always require a human.
- Refunds, billing disputes, security incidents and data deletion always require a human, enforced in the prompt and again in code.
- The assistant never approves refunds or gives discounts, and it says it is an AI if asked.
- Empty or invalid model output is stored as a failed ticket with a clear error instead of crashing.
- LLM calls retry with backoff on temporary errors such as rate limits, and the voice path can fall back to a second model.
- The voice endpoints are protected by a shared secret header.

## Run it

Needs Docker and an OpenRouter API key.

1. Copy `.env.example` to `.env` and fill in the values below.
2. Start everything:

       docker compose up --build

3. Open http://localhost:3000 (API docs: http://localhost:8000/docs).

The first start downloads a small embedding model, so the backend needs a minute before it is ready.

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | LLM access through OpenRouter |
| `LLM_MODEL` | Model for the ticket pipeline (for example `google/gemini-2.5-flash-lite`) |
| `VOICE_LLM_MODEL` | Faster model for live answers (empty = same as `LLM_MODEL`) |
| `VOICE_FALLBACK_MODEL` | Optional second model used if the voice model keeps failing |
| `VOICE_API_SECRET` | Shared secret the voice platform sends in the `X-Voice-Secret` header |
| `RAG_MODE` | `vector` (default), `hybrid` or `rerank` |
| `RAG_MIN_SCORE` | Minimum similarity for an answer to count as found (0.6 works for the demo documents) |
| `DOMAIN` | Domain used by Caddy for HTTPS in production |

Do not put spaces around `=` or quotes around values in `.env`.

For the live server use `docker compose -f docker-compose.prod.yml up -d --build`.

**Without Docker** (Python 3.11 or 3.12, Node 18 or newer):

```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --reload-dir app

cd frontend
npm install
npm run dev
```

To use your own documents, replace the Markdown files in `backend/knowledge/` and restart.

To connect a Bolna agent, the server needs a public HTTPS URL. Point the agent's custom function at `/api/voice/ask` and its webhook at `/api/voice/webhook`, both with the `X-Voice-Secret` header.

## Scripts

Run these from the `backend` folder.

| Script | What it does |
|--------|--------------|
| `scripts/ask.py "question"` | Ask the knowledge base from the terminal |
| `scripts/eval_retrieval.py compare` | Compare vector, hybrid and rerank retrieval on the labeled questions |
| `scripts/eval_answers.py` | End-to-end check that unanswerable questions are refused |
| `scripts/measure_latency.py <url>` | Time the answer endpoint |
| `scripts/send_test_webhook.py [url]` | Send a fake finished call and create a ticket |
| `scripts/seed_demo_calls.py <url>` | Create sample tickets from simulated call transcripts |

## API

```
POST /api/tickets            process one ticket
GET  /api/tickets            list with filters and pagination
GET  /api/tickets/{id}       ticket detail
GET  /api/stats              dashboard numbers
POST /api/voice/ask          knowledge base answer for the voice agent
POST /api/voice/webhook      finished call, creates a ticket
GET  /api/health
```

## Project structure

```
backend/
  app/            FastAPI app, LangChain chains, RAG, routers
  prompts/        triage, analysis, resolution and reply prompts
  knowledge/      demo knowledge base (Markdown)
  scripts/        evaluation, latency and test scripts
frontend/         React + Vite + Tailwind dashboard
docker-compose.yml, docker-compose.prod.yml, Caddyfile
```

## Limitations and next steps

- Public demo protections: Nginx rate limiting, and delete and batch endpoints are disabled.
- No user authentication on the dashboard yet.
- Audit logging is basic: call transcripts and ticket outcomes are stored and each knowledge-base lookup is logged, but there is no structured trace per tool call.
- No automated unit tests yet (there are evaluation scripts).
- SQLite on a single instance is fine for a demo, not for production traffic.
- The evaluation uses synthetic documents and questions written by me. Next step is the same evaluation on messier real documents.
- Speech recognition quality depends on the voice platform and accents.
- Related work: more advanced RAG techniques are explored in my Advance-RAG repository.

## Tech stack

Python, FastAPI, LangChain, Pydantic, SQLAlchemy, SQLite, fastembed, Bolna, OpenRouter, React, Vite, Tailwind CSS, Docker, Nginx, Caddy, AWS EC2.
