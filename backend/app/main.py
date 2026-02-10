from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

import subprocess

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .config import EVENTS_PATH
from .db import fetch_all, fetch_one, init_db
from .services.event_ingest import Tailer, TmuxWatcher
from .services.tmux_probe import map_agents, pane_is_responsive, capture_pane, detect_auth_needed

app = FastAPI(title="CodexDash API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"]
)


class ConnectionManager:
  def __init__(self) -> None:
    self.active: List[WebSocket] = []

  async def connect(self, websocket: WebSocket) -> None:
    await websocket.accept()
    self.active.append(websocket)

  def disconnect(self, websocket: WebSocket) -> None:
    if websocket in self.active:
      self.active.remove(websocket)

  async def broadcast(self, message: Dict[str, Any]) -> None:
    if not self.active:
      return
    data = json.dumps(message, ensure_ascii=False)
    for ws in list(self.active):
      try:
        await ws.send_text(data)
      except WebSocketDisconnect:
        self.disconnect(ws)
      except Exception:
        self.disconnect(ws)


manager = ConnectionManager()


tailer = Tailer()
watcher = TmuxWatcher()


@app.on_event("startup")
async def startup() -> None:
  init_db()
  asyncio.create_task(tailer.run(manager.broadcast))
  asyncio.create_task(watcher.run(manager.broadcast))


@app.get("/api/health")
async def health() -> Dict[str, Any]:
  return {"ok": True, "ts": int(time.time() * 1000)}


@app.get("/api/agents")
async def agents() -> List[Dict[str, Any]]:
  rows = fetch_all("SELECT * FROM agents ORDER BY agent")
  return rows


@app.get("/api/jobs")
async def jobs(limit: int = 50, status: Optional[str] = None, agent: Optional[str] = None) -> List[Dict[str, Any]]:
  clauses = []
  params = []
  if status:
    clauses.append("status = ?")
    params.append(status)
  if agent:
    clauses.append("agent = ?")
    params.append(agent)
  where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
  query = f"SELECT * FROM jobs {where} ORDER BY updated_ts DESC LIMIT ?"
  params.append(limit)
  rows = fetch_all(query, params)
  return rows


@app.get("/api/jobs/{job_id}")
async def job_detail(job_id: str) -> Dict[str, Any]:
  job = fetch_one("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
  events = fetch_all("SELECT * FROM events WHERE job_id = ? ORDER BY ts", (job_id,))
  return {"job": job, "events": events}


@app.get("/api/events")
async def events(since: Optional[int] = None, limit: int = 200) -> List[Dict[str, Any]]:
  if since is None:
    rows = fetch_all("SELECT * FROM events ORDER BY ts DESC LIMIT ?", (limit,))
  else:
    rows = fetch_all("SELECT * FROM events WHERE ts >= ? ORDER BY ts DESC LIMIT ?", (since, limit))
  return rows


@app.get("/api/doctor")
async def doctor() -> Dict[str, Any]:
  mapping = map_agents()
  status = {}
  for agent, info in mapping.items():
    pane_id = info.get("pane_id")
    responsive = pane_is_responsive(pane_id) if pane_id else False
    pane_text = capture_pane(pane_id, lines=30) if pane_id else ""
    status[agent] = {
      "pane_id": pane_id,
      "window_name": info.get("window_name"),
      "responsive": responsive,
      "auth_needed": detect_auth_needed(pane_text),
      "mode": info.get("mode"),
    }
  return {"agents": status}


@app.post("/api/dispatch")
async def dispatch(payload: Dict[str, Any]) -> Dict[str, Any]:
  targets = payload.get("targets") or []
  prompt = payload.get("prompt") or ""
  parallel = payload.get("parallel")
  wait = payload.get("wait")
  outdir = payload.get("outdir")
  job_id = payload.get("job_id") or None

  cmd = ["/home/chaithupi5/bin/codexdash", "send"]
  if isinstance(targets, list):
    cmd.extend([f"@{t}" for t in targets])
  if parallel is not None:
    cmd.extend(["--parallel", str(int(bool(parallel)))])
  if wait is not None:
    cmd.extend(["--wait", str(int(bool(wait)))])
  if outdir:
    cmd.extend(["--outdir", str(outdir)])
  if prompt:
    cmd.extend(["--prompt", prompt])

  env = dict(**os.environ)
  if job_id:
    env["CODEXDASH_JOB_ID"] = str(job_id)

  proc = subprocess.Popen(cmd, env=env)
  return {"ok": True, "pid": proc.pid, "job_id": job_id}


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
  await manager.connect(websocket)
  try:
    while True:
      await websocket.receive_text()
  except WebSocketDisconnect:
    manager.disconnect(websocket)
