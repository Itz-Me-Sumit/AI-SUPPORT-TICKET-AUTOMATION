# AI Support Ticket Automation, now with a voice helpdesk

A customer calls, an AI voice agent answers from the company knowledge base, and every call is turned into a triaged support ticket with a drafted reply. Refunds and other money decisions are never made by the AI: they always go to a human.

> TechNova is a fictional company. The knowledge base in `backend/knowledge/` is a demo dataset, and the prices and policies in it are made up. Swap in real documents to use it for a real company.

**Live demo:** https://3-107-146-58.sslip.io/ (dashboard with processed tickets)

## What it does

**During the call**
1. The customer talks to a voice agent built on Bolna.
2. For product, billing and policy questions the agent calls `POST /api/voice/ask`.
3. The backend retrieves matching chunks from the knowledge base (embedding search), then writes a short spoken answer using only that context. If nothing relevant is found, it says it does not know instead of guessing.

**After the call**
1. Bolna sends the finished call to `POST /api/voice/webhook`.
2. A four-stage LangChain pipeline runs on the transcript: triage (category, priority, language), category-specific analysis, resolution decision, and a drafted customer reply. Every stage returns validated Pydantic output.
3. The ticket appears in the dashboard with a Voice badge and the call transcript.

**Safety rules**
- Critical tickets always require a human.
- Refunds, billing disputes, security incidents and data deletion always require a human, enforced in the prompt and again in code.
- Empty or invalid model output is stored as a failed ticket with a clear error instead of crashing.
- LLM calls retry with backoff on temporary errors such as rate limits, and the voice path can fall back to a second model.
- The voice endpoints are protected by a shared secret header.

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

## Retrieval evaluation (internal)

I compared three retrieval modes on 50 labeled questions (25 close to the documents, 25 paraphrased or spoken-style) plus 13 questions the documents cannot answer. No LLM calls are involved in this table.

| Mode | Easy hit@1 | Hard hit@1 | Hard hit@3 | Hard MRR |
|------|-----------|-----------|-----------|----------|
| vector (used) | 96% | 80% | 96% | 0.873 |
| hybrid (vector + BM25) | 92% | 72% | 100% | 0.853 |
| rerank (hybrid + cross-encoder) | 92% | 80% | 96% | 0.880 |

On this small, cleanly structured knowledge base (77 chunks), hybrid search and reranking gave no measurable gain over plain vector search, so the demo keeps vector search. Differences of one or two questions are noise at this size. These numbers come from a synthetic dataset I wrote myself, so they say little about real-world accuracy.

Answer safety check: for the 13 unanswerable questions, retrieval alone stopped 7. The answer prompt refused the remaining 6, so the pipeline said it did not know on all 13. Run `python scripts/eval_answers.py` to reproduce.

## Run it

Needs Docker and an OpenRouter API key.

1. Copy `.env.example` to `.env` and fill in the values below.
2. Start everything:

       docker compose up --build

3. Open http://localhost:3000 (API docs: http://localhost:8000/docs).

| Variable | Purpose |
|----------|---------|
| `OPENROUTER_API_KEY` | LLM access through OpenRouter |
| `LLM_MODEL` | Model for the ticket pipeline |
| `VOICE_LLM_MODEL` | Faster model for live answers (empty = same as `LLM_MODEL`) |
| `VOICE_FALLBACK_MODEL` | Optional second model used if the voice model keeps failing |
| `VOICE_API_SECRET` | Shared secret the voice platform sends in the `X-Voice-Secret` header |
| `RAG_MODE` | `vector` (default), `hybrid` or `rerank` |
| `RAG_MIN_SCORE` | Minimum similarity for an answer to count as found |

For the live server use `docker compose -f docker-compose.prod.yml up -d --build` and set `DOMAIN` to your domain.

To use your own documents, replace the Markdown files in `backend/knowledge/` and restart.

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
  scripts/        evaluation and test scripts
frontend/         React + Vite + Tailwind dashboard
docker-compose.yml, docker-compose.prod.yml, Caddyfile
```

## Limitations and next steps

- Public demo protections: Nginx rate limiting, and delete and batch endpoints are disabled.
- No user authentication on the dashboard yet.
- No automated unit tests yet (there are evaluation scripts).
- Speech recognition quality depends on the voice platform and accents.
- Related work: more advanced RAG techniques are explored in my Advance-RAG repository.

## Tech stack

Python, FastAPI, LangChain, Pydantic, SQLAlchemy, SQLite, fastembed, Bolna, OpenRouter, React, Vite, Tailwind CSS, Docker, Nginx, Caddy, AWS EC2.
