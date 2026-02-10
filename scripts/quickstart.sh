#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
BIN_DIR="$HOME/bin"

log() { printf "\n[%s] %s\n" "$(date +%H:%M:%S)" "$*"; }

log "Installing system dependencies (best-effort)"
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-venv python3-pip nodejs npm tmux curl
else
  log "apt-get not found; please ensure python3, nodejs, npm, tmux are installed"
fi

log "Installing codexctl + codexdash to ~/bin"
mkdir -p "$BIN_DIR"
if [ -f "$ROOT_DIR/tmux/codexctl/codexctl" ]; then
  cp -a "$ROOT_DIR/tmux/codexctl/codexctl" "$BIN_DIR/codexctl"
  chmod +x "$BIN_DIR/codexctl"
fi
if [ -f "$ROOT_DIR/tmux/codexctl/install.sh" ]; then
  cp -a "$ROOT_DIR/tmux/codexctl/install.sh" "$BIN_DIR/codexctl-install.sh"
  chmod +x "$BIN_DIR/codexctl-install.sh"
fi
if [ -f "$ROOT_DIR/bin/codexdash" ]; then
  cp -a "$ROOT_DIR/bin/codexdash" "$BIN_DIR/codexdash"
  chmod +x "$BIN_DIR/codexdash"
fi

log "Setting up backend venv"
cd "$BACKEND_DIR"
python3 -m venv .venv
# shellcheck disable=SC1091
. .venv/bin/activate
pip install -r requirements.txt

log "Installing frontend dependencies"
cd "$FRONTEND_DIR"
npm install

log "Initializing local data directory"
mkdir -p "$HOME/.codexdash"
: > "$HOME/.codexdash/events.ndjson"

log "Starting backend on :8090"
pkill -f "uvicorn app.main:app" || true
cd "$BACKEND_DIR"
# shellcheck disable=SC1091
. .venv/bin/activate
setsid -f uvicorn app.main:app --host 0.0.0.0 --port 8090 > /tmp/codexdash_backend.log 2>&1

log "Starting frontend on :5173"
pkill -f "vite --host 0.0.0.0 --port 5173" || true
cd "$FRONTEND_DIR"
setsid -f node ./node_modules/.bin/vite --host 0.0.0.0 --port 5173 > /tmp/codexdash_frontend.log 2>&1

log "Starting tmux agents"
if [ -x "$BIN_DIR/codexctl" ]; then
  "$BIN_DIR/codexctl" up --agents "fast,deep,test,sec" --windows --noattach || true
else
  log "codexctl not found; skipping agent startup"
fi

log "Done"
log "Frontend: http://localhost:5173"
log "Backend:  http://localhost:8090"
log "Logs: /tmp/codexdash_frontend.log and /tmp/codexdash_backend.log"
