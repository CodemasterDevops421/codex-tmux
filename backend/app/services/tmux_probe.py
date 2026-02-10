from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional

from ..config import DEFAULT_SESSION

AGENTS = ["fast", "deep", "test", "sec"]


def _run_tmux(args: list[str]) -> str:
  result = subprocess.run(["tmux", *args], capture_output=True, text=True)
  if result.returncode != 0:
    return ""
  return result.stdout.strip()


def detect_session() -> str:
  return os.environ.get("CODEX_TMUX_SESSION", DEFAULT_SESSION)


def list_windows(session: str) -> list[dict]:
  out = _run_tmux(["list-windows", "-t", session, "-F", "#{window_index}::#{window_name}"])
  windows = []
  for line in out.splitlines():
    if not line:
      continue
    idx, name = line.split("::", 1)
    windows.append({"index": idx, "name": name})
  return windows


def list_panes(session: str) -> list[dict]:
  out = _run_tmux([
    "list-panes",
    "-t",
    session,
    "-F",
    "#{pane_id}::#{pane_title}::#{pane_current_command}::#{window_name}",
  ])
  panes = []
  for line in out.splitlines():
    if not line:
      continue
    parts = line.split("::")
    if len(parts) < 4:
      continue
    pane_id, title, cmd, window = parts[0], parts[1], parts[2], parts[3]
    panes.append({"pane_id": pane_id, "title": title, "cmd": cmd, "window": window})
  return panes


def _get_option(session: str, name: str) -> str:
  return _run_tmux(["show-option", "-gqv", name])


def map_agents(session: Optional[str] = None) -> Dict[str, dict]:
  session = session or detect_session()
  mapping: Dict[str, dict] = {}

  # windows mode: window names are agent names
  windows = list_windows(session)
  window_names = {w["name"]: w for w in windows}
  if all(agent in window_names for agent in AGENTS):
    panes = list_panes(session)
    for agent in AGENTS:
      pane = next((p for p in panes if p["window"] == agent), None)
      if pane:
        mapping[agent] = {
          "pane_id": pane["pane_id"],
          "window_name": agent,
          "mode": "windows",
        }
    return mapping

  # pane mode: use tmux options @codexctl_pane_* if present
  panes = list_panes(session)
  for agent in AGENTS:
    opt = _get_option(session, f"@codexctl_pane_{agent}")
    if opt:
      pane = next((p for p in panes if p["pane_id"] == opt or p["window"] == opt), None)
      if pane:
        mapping[agent] = {
          "pane_id": pane["pane_id"],
          "window_name": pane["window"],
          "mode": "panes",
        }

  # inference by title or command
  for agent in AGENTS:
    if agent in mapping:
      continue
    pane = next(
      (p for p in panes if agent in p["title"].lower() or agent in p["cmd"].lower()),
      None,
    )
    if pane:
      mapping[agent] = {
        "pane_id": pane["pane_id"],
        "window_name": pane["window"],
        "mode": "panes",
      }

  return mapping


def capture_pane(pane_id: str, lines: int = 2000) -> str:
  return _run_tmux(["capture-pane", "-p", "-t", pane_id, "-S", f"-{lines}"])


def pane_is_responsive(pane_id: str) -> bool:
  out = _run_tmux(["capture-pane", "-p", "-t", pane_id, "-S", "-10"])
  return bool(out)


def detect_auth_needed(text: str) -> bool:
  lowered = text.lower()
  return (
    "sign in" in lowered
    or "log in" in lowered
    or "authenticate" in lowered
    or "approval" in lowered
    or "openai" in lowered and "browser" in lowered
  )
