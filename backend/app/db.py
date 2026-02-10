from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .config import DB_PATH, CODEXDASH_DIR

_DB_LOCK = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
  agent TEXT PRIMARY KEY,
  status TEXT,
  last_seen INTEGER,
  pane_id TEXT,
  window_name TEXT,
  session TEXT,
  model TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  agent TEXT,
  status TEXT,
  started_ts INTEGER,
  updated_ts INTEGER,
  duration_ms INTEGER,
  prompt_text TEXT,
  prompt_hash TEXT,
  prompt_bytes INTEGER,
  output_path TEXT,
  output_bytes INTEGER,
  model TEXT,
  prompt_tokens_exact INTEGER,
  completion_tokens_exact INTEGER,
  total_tokens_exact INTEGER,
  prompt_tokens_est INTEGER,
  completion_tokens_est INTEGER,
  total_tokens_est INTEGER
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER,
  type TEXT,
  session TEXT,
  agent TEXT,
  pane_id TEXT,
  window_name TEXT,
  job_id TEXT,
  payload TEXT,
  prompt_text TEXT,
  prompt_hash TEXT,
  prompt_bytes INTEGER,
  output_path TEXT,
  output_bytes INTEGER,
  model TEXT,
  prompt_tokens_exact INTEGER,
  completion_tokens_exact INTEGER,
  total_tokens_exact INTEGER,
  prompt_tokens_est INTEGER,
  completion_tokens_est INTEGER,
  total_tokens_est INTEGER
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id);
CREATE INDEX IF NOT EXISTS idx_jobs_agent ON jobs(agent);
"""


def init_db() -> None:
  CODEXDASH_DIR.mkdir(parents=True, exist_ok=True)
  with _DB_LOCK:
    attempts = 0
    while True:
      try:
        conn = _connect()
        try:
          conn.execute("PRAGMA journal_mode=WAL;")
          conn.executescript(SCHEMA)
          conn.commit()
        finally:
          conn.close()
        break
      except sqlite3.OperationalError as exc:
        attempts += 1
        if "locked" not in str(exc).lower() or attempts >= 10:
          raise
        time.sleep(0.2)


def _connect() -> sqlite3.Connection:
  conn = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
  conn.row_factory = sqlite3.Row
  conn.execute("PRAGMA synchronous=NORMAL;")
  conn.execute("PRAGMA busy_timeout=5000;")
  return conn


def insert_event(event: Dict[str, Any]) -> None:
  with _DB_LOCK:
    conn = _connect()
    try:
      conn.execute(
        """
        INSERT INTO events (
          ts, type, session, agent, pane_id, window_name, job_id, payload,
          prompt_text, prompt_hash, prompt_bytes,
          output_path, output_bytes, model,
          prompt_tokens_exact, completion_tokens_exact, total_tokens_exact,
          prompt_tokens_est, completion_tokens_est, total_tokens_est
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
          event.get("ts"),
          event.get("type"),
          event.get("session"),
          event.get("agent"),
          event.get("pane_id"),
          event.get("window_name"),
          event.get("job_id"),
          json.dumps(event, ensure_ascii=False),
          event.get("prompt_text"),
          event.get("prompt_hash"),
          event.get("prompt_bytes"),
          event.get("output_path"),
          event.get("output_bytes"),
          event.get("model"),
          event.get("prompt_tokens_exact"),
          event.get("completion_tokens_exact"),
          event.get("total_tokens_exact"),
          event.get("prompt_tokens_est"),
          event.get("completion_tokens_est"),
          event.get("total_tokens_est"),
        ),
      )
      conn.commit()
    finally:
      conn.close()


def upsert_agent(agent: Dict[str, Any]) -> None:
  with _DB_LOCK:
    conn = _connect()
    try:
      conn.execute(
        """
        INSERT INTO agents (agent, status, last_seen, pane_id, window_name, session, model)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(agent) DO UPDATE SET
          status=excluded.status,
          last_seen=excluded.last_seen,
          pane_id=excluded.pane_id,
          window_name=excluded.window_name,
          session=excluded.session,
          model=excluded.model
        """,
        (
          agent.get("agent"),
          agent.get("status"),
          agent.get("last_seen"),
          agent.get("pane_id"),
          agent.get("window_name"),
          agent.get("session"),
          agent.get("model"),
        ),
      )
      conn.commit()
    finally:
      conn.close()


def upsert_job(job: Dict[str, Any]) -> None:
  with _DB_LOCK:
    conn = _connect()
    try:
      conn.execute(
        """
        INSERT INTO jobs (
          job_id, agent, status, started_ts, updated_ts, duration_ms,
          prompt_text, prompt_hash, prompt_bytes,
          output_path, output_bytes, model,
          prompt_tokens_exact, completion_tokens_exact, total_tokens_exact,
          prompt_tokens_est, completion_tokens_est, total_tokens_est
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
          agent=excluded.agent,
          status=excluded.status,
          started_ts=COALESCE(jobs.started_ts, excluded.started_ts),
          updated_ts=excluded.updated_ts,
          duration_ms=excluded.duration_ms,
          prompt_text=COALESCE(jobs.prompt_text, excluded.prompt_text),
          prompt_hash=COALESCE(jobs.prompt_hash, excluded.prompt_hash),
          prompt_bytes=COALESCE(jobs.prompt_bytes, excluded.prompt_bytes),
          output_path=COALESCE(jobs.output_path, excluded.output_path),
          output_bytes=COALESCE(jobs.output_bytes, excluded.output_bytes),
          model=COALESCE(jobs.model, excluded.model),
          prompt_tokens_exact=COALESCE(jobs.prompt_tokens_exact, excluded.prompt_tokens_exact),
          completion_tokens_exact=COALESCE(jobs.completion_tokens_exact, excluded.completion_tokens_exact),
          total_tokens_exact=COALESCE(jobs.total_tokens_exact, excluded.total_tokens_exact),
          prompt_tokens_est=COALESCE(jobs.prompt_tokens_est, excluded.prompt_tokens_est),
          completion_tokens_est=COALESCE(jobs.completion_tokens_est, excluded.completion_tokens_est),
          total_tokens_est=COALESCE(jobs.total_tokens_est, excluded.total_tokens_est)
        """,
        (
          job.get("job_id"),
          job.get("agent"),
          job.get("status"),
          job.get("started_ts"),
          job.get("updated_ts"),
          job.get("duration_ms"),
          job.get("prompt_text"),
          job.get("prompt_hash"),
          job.get("prompt_bytes"),
          job.get("output_path"),
          job.get("output_bytes"),
          job.get("model"),
          job.get("prompt_tokens_exact"),
          job.get("completion_tokens_exact"),
          job.get("total_tokens_exact"),
          job.get("prompt_tokens_est"),
          job.get("completion_tokens_est"),
          job.get("total_tokens_est"),
        ),
      )
      conn.commit()
    finally:
      conn.close()


def fetch_all(query: str, params: Iterable[Any] = ()) -> list[Dict[str, Any]]:
  with _DB_LOCK:
    conn = _connect()
    try:
      rows = conn.execute(query, params).fetchall()
      return [dict(row) for row in rows]
    finally:
      conn.close()


def fetch_one(query: str, params: Iterable[Any] = ()) -> Optional[Dict[str, Any]]:
  with _DB_LOCK:
    conn = _connect()
    try:
      row = conn.execute(query, params).fetchone()
      return dict(row) if row else None
    finally:
      conn.close()
