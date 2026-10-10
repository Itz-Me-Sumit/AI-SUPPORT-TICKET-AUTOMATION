import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401 - registers the tables on Base
from app.config import settings
from app.database import Base, engine
from app.llm import get_llm
from app.routers import tickets
from app.workflow import build_workflow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables and build the LLM chains once at startup
    Base.metadata.create_all(bind=engine)
    app.state.workflow = build_workflow(get_llm())
    yield


app = FastAPI(
    title="AI Support Ticket Automation",
    description="Triage, analyse, resolve and reply to support tickets with LLM chains.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets.router)
