from __future__ import annotations

import pathlib

from dotenv import load_dotenv

load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import db
import graphdb_client
import ingestion
import snapshots
from routers import assess, explain, corpus, snapshots as snapshots_router, checloud as checloud_router, mapping_info, sparql as sparql_router, ingestion as ingestion_router

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if db.is_postgres_enabled():
        try:
            db.ensure_seeded()
        except Exception as exc:


            print(f"[startup] Postgres seeding skipped ({exc}); "
                  f"falling back to CSV corpus for now.")

    if graphdb_client.is_enabled():
        try:
            graphdb_client.ensure_seeded()
        except Exception as exc:


            print(f"[startup] GraphDB seeding skipped ({exc}); "
                  f"falling back to in-memory SPARQL graph for now.")

    if not snapshots.list_snapshots():
        snapshots.create_snapshot()


    scheduler.add_job(
        ingestion.run_monthly_ingestion,
        CronTrigger(day=1, hour=2, minute=0),
        id="monthly_ingestion",
        replace_existing=True,
    )
    scheduler.add_job(
        snapshots.create_snapshot,
        CronTrigger(day=1, hour=3, minute=0),
        id="monthly_snapshot",
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(
    title="Multi-Tool FAIR Assessment API",
    description="Runs F-UJI, FAIR-Checker, and KGHeartBeat against a resource, "
                "normalises results onto a shared mapping, computes cross-tool "
                "consensus, and generates an OpenAI explanation. Also archives "
                "monthly snapshots of the full corpus assessment, downloadable "
                "the same way KGHeartBeat's own periodic archive works.",
    version="1.0.0",
    lifespan=lifespan,
)

_default_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
_extra = os.environ.get("FRONTEND_ORIGINS", "")
origins = _default_origins + [o.strip() for o in _extra.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(assess.router, tags=["assess"])
app.include_router(explain.router, tags=["explain"])
app.include_router(corpus.router, tags=["corpus"])
app.include_router(snapshots_router.router, tags=["snapshots"])
app.include_router(checloud_router.router, tags=["checloud"])
app.include_router(mapping_info.router, tags=["mapping"])
app.include_router(sparql_router.router, tags=["sparql"])
app.include_router(ingestion_router.router, tags=["ingestion"])


@app.get("/health")
async def health():
    return {"status": "ok"}
