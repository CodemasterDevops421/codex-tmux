from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .token_estimate import estimate_tokens
from .tmux_probe import AGENTS, capture_pane, detect_auth_needed, map_agents
from ..config import EVENTS_PATH, TAIL_INTERVAL_MS, MAX_EVENT_LINE
from ..db import insert_event, upsert_agent, upsert_job, fetch_one

TOKEN_REGEX = re.compile(r"(prompt|completion|total)\s*tokens\s*[:=]\s*(\d+)", re.I)
MODEL_REGEX = re.compile(r"model\s*[:=]\s*([\w\-\.]+)", re.I)
SUB_AGENT_REGEX = re.compile(r"(sub-?agent|tool|thread)\s*[:#]\s*([\w\-\.]+)", re.I)
JOB_REGEX = re.compile(r"\[JOB:([a-f0-9\\-]{8,})\]", re.I)
DONE_REGEX = re.compile(r"\b(done|completed|success|finished)\b", re.I)
ERROR_REGEX = re.compile(r"\b(error|failed|traceback|exception)\b", re.I)


def _hash_text(text: str) -> str:
  return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def parse_tokens(text: str) -> dict[str, Optional[int]]:
  found = {"prompt": None, "completion": None, "total": None}
  for key, val in TOKEN_REGEX.findall(text):
    found[key.lower()] = int(val)
  return found


def detect_model(text: str) -> Optional[str]:
  match = MODEL_REGEX.search(text)
  return match.group(1) if match else None


def detect_subagent(text: str) -> Optional[str]:
  match = SUB_AGENT_REGEX.search(text)
  if match:
    return match.group(2)
  return None


def classify_status(text: str) -> Optional[str]:
  if not text:
    return None
  if ERROR_REGEX.search(text):
    return "error"
  if detect_auth_needed(text):
    return "blocked"
  if DONE_REGEX.search(text):
    return "done"
  return None


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
  prompt_text = event.get("prompt_text") or ""
  if prompt_text and len(prompt_text) > 10000:
    event["prompt_hash"] = _hash_text(prompt_text)
    event["prompt_text"] = None
  elif prompt_text:
    event["prompt_hash"] = _hash_text(prompt_text)

  if "prompt_bytes" not in event or event.get("prompt_bytes") is None:
    event["prompt_bytes"] = len(prompt_text.encode("utf-8")) if prompt_text else 0

  return event


def update_job_from_event(event: Dict[str, Any]) -> None:
  job_id = event.get("job_id")
  if not job_id:
    return

  now = event.get("ts") or int(time.time() * 1000)
  status = event.get("status")
  if event.get("type") == "dispatch":
    status = "running"
  if status is None and event.get("type") in {"pane_output", "controller_output"}:
    status = "running"

  tokens_exact = {
    "prompt": event.get("prompt_tokens_exact"),
    "completion": event.get("completion_tokens_exact"),
    "total": event.get("total_tokens_exact"),
  }

  tokens_est = {
    "prompt": event.get("prompt_tokens_est"),
    "completion": event.get("completion_tokens_est"),
    "total": event.get("total_tokens_est"),
  }

  job = {
    "job_id": job_id,
    "agent": event.get("agent"),
    "status": status,
    "started_ts": event.get("ts") if event.get("type") == "dispatch" else None,
    "updated_ts": now,
    "duration_ms": None,
    "prompt_text": event.get("prompt_text"),
    "prompt_hash": event.get("prompt_hash"),
    "prompt_bytes": event.get("prompt_bytes"),
    "output_path": event.get("output_path"),
    "output_bytes": event.get("output_bytes"),
    "model": event.get("model"),
    "prompt_tokens_exact": tokens_exact.get("prompt"),
    "completion_tokens_exact": tokens_exact.get("completion"),
    "total_tokens_exact": tokens_exact.get("total"),
    "prompt_tokens_est": tokens_est.get("prompt"),
    "completion_tokens_est": tokens_est.get("completion"),
    "total_tokens_est": tokens_est.get("total"),
  }

  existing = fetch_one("SELECT started_ts FROM jobs WHERE job_id = ?", (job_id,))
  started_ts = existing.get("started_ts") if existing else None
  if started_ts and status in {"done", "error", "blocked"}:
    job["duration_ms"] = now - int(started_ts)

  upsert_job(job)

  agent = {
    "agent": event.get("agent"),
    "status": status or "running",
    "last_seen": now,
    "pane_id": event.get("pane_id"),
    "window_name": event.get("window_name"),
    "session": event.get("session"),
    "model": event.get("model"),
  }
  if agent.get("agent"):
    upsert_agent(agent)


def enrich_output_event(event: Dict[str, Any]) -> Dict[str, Any]:
  text = event.get("text", "")
  if not event.get("job_id") and text:
    match = JOB_REGEX.search(text)
    if match:
      event["job_id"] = match.group(1)
  tokens = parse_tokens(text)
  event["prompt_tokens_exact"] = tokens.get("prompt")
  event["completion_tokens_exact"] = tokens.get("completion")
  event["total_tokens_exact"] = tokens.get("total")
  if not event.get("model"):
    event["model"] = detect_model(text)

  status = classify_status(text)
  if status:
    event["status"] = status

  if event.get("prompt_text"):
    event["prompt_tokens_est"] = estimate_tokens(event["prompt_text"])

  if text:
    event["completion_tokens_est"] = estimate_tokens(text)
    if event.get("prompt_tokens_est") is not None:
      event["total_tokens_est"] = event["prompt_tokens_est"] + event["completion_tokens_est"]

  sub_agent = detect_subagent(text)
  if sub_agent:
    event["sub_agent"] = sub_agent

  return event


class Tailer:
  def __init__(self) -> None:
    self._offset = 0

  async def run(self, on_event) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_PATH.touch(exist_ok=True)
    while True:
      events = await asyncio.to_thread(self._process_events)
      for event in events:
        await on_event(event)
      await asyncio.sleep(TAIL_INTERVAL_MS / 1000.0)

  def _process_events(self) -> list[Dict[str, Any]]:
    if not EVENTS_PATH.exists():
      return []
    processed: list[Dict[str, Any]] = []
    with EVENTS_PATH.open("r", encoding="utf-8", errors="ignore") as f:
      f.seek(self._offset)
      for line in f:
        if not line.strip():
          continue
        if len(line) > MAX_EVENT_LINE:
          continue
        try:
          event = json.loads(line)
        except json.JSONDecodeError:
          continue
        event = normalize_event(event)
        event = enrich_output_event(event)
        insert_event(event)
        update_job_from_event(event)
        processed.append(event)
      self._offset = f.tell()
    return processed


class TmuxWatcher:
  def __init__(self) -> None:
    self._last_seen: dict[str, int] = {}
    self._last_text: dict[str, str] = {}

  async def run(self, on_event) -> None:
    while True:
      events = await asyncio.to_thread(self._poll)
      for event in events:
        await on_event(event)
      await asyncio.sleep(TAIL_INTERVAL_MS / 1000.0)

  def _poll(self) -> list[Dict[str, Any]]:
    mapping = map_agents()
    now = int(time.time() * 1000)
    emitted: list[Dict[str, Any]] = []
    for agent, info in mapping.items():
      pane_id = info.get("pane_id")
      if not pane_id:
        continue
      text = capture_pane(pane_id, lines=2000)
      if not text:
        continue
      prev = self._last_text.get(pane_id, "")
      if text == prev:
        continue
      self._last_text[pane_id] = text
      new_text = text[len(prev):] if text.startswith(prev) else text
      new_text = new_text.strip("\n")
      if not new_text:
        continue
      event = {
        "ts": now,
        "type": "pane_output",
        "session": None,
        "agent": agent,
        "pane_id": pane_id,
        "window_name": info.get("window_name"),
        "job_id": None,
        "text": new_text,
      }
      event = enrich_output_event(event)
      insert_event(event)
      update_job_from_event(event)
      emitted.append(event)

      if detect_auth_needed(new_text):
        upsert_agent({
          "agent": agent,
          "status": "blocked",
          "last_seen": now,
          "pane_id": pane_id,
          "window_name": info.get("window_name"),
          "session": None,
          "model": event.get("model"),
        })
    return emitted
