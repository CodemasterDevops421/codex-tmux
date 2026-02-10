# codexctl (tmux parallel Codex agents)

## Install
```bash
~/codexctl/install.sh
source ~/.bashrc
```

## Start 4 agents (fast, deep, test, sec)
```bash
mkdir -p ~/work/tmux
~/bin/codexctl up --dir ~/work/tmux --agents "fast,deep,test,sec" --noattach
~/bin/codexctl attach
```

### Switch tmux panes
- Next pane: `Ctrl-b o`
- Previous pane: `Ctrl-b ;`
- Directional: `Ctrl-b` + Arrow keys
- Detach: `Ctrl-b d`

## Show agent mapping
```bash
~/bin/codexctl ids
```

## Send prompts (RFC-safe)
```bash
mkdir -p /tmp/codex_out

~/bin/codexctl send @1 --wait 120 --outdir /tmp/codex_out -- "Say hello"
~/bin/codexctl send @fast --wait 120 --outdir /tmp/codex_out -- "Quick refactor suggestions."
~/bin/codexctl send all --parallel --wait 120 --outdir /tmp/codex_out -- "Summarize repo risks."
~/bin/codexctl send @2 --wait 120 --outdir /tmp/codex_out -- - < prompt.txt
ls -ltr /tmp/codex_out
```

## Route by complexity (auto-pick agent)
```bash
~/bin/codexctl route --outdir /tmp/codex_out -- "Write unit tests for quicklife_validate_html.js"
~/bin/codexctl route --outdir /tmp/codex_out -- "Security review: secrets & injection risks in this repo"
~/bin/codexctl route --outdir /tmp/codex_out -- "Design architecture for new feature and rollout plan"
```

## Ship a feature (parallel plan/test/sec + implement)
```bash
~/bin/codexctl ship "Add feature flag for autopost scheduling and rollback."
```

Outputs go to `/tmp/codex_ship_<timestamp>/`.

## Optional: different models/profiles per agent
Launch with per-agent profiles/models:
```bash
~/bin/codexctl down

~/bin/codexctl up --dir ~/work/tmux \
  --agents   "fast,deep,test,sec" \
  --profiles "fast,deep,fast,deep" \
  --models   ",,," \
  --noattach

~/bin/codexctl attach
```

## Avoid "no space for new pane" (small terminals)
Use window-per-agent mode:
```bash
~/bin/codexctl down
~/bin/codexctl up --dir ~/work/tmux --agents "fast,deep,test,sec" --windows
~/bin/codexctl attach
```

Or use a different layout:
```bash
~/bin/codexctl down
~/bin/codexctl up --dir ~/work/tmux --agents "fast,deep,test,sec" --layout even-vertical
~/bin/codexctl attach
```

## Optional: bypass approvals/sandbox (use only if you really want it)
This starts each Codex pane with `--dangerously-bypass-approvals-and-sandbox`.
```bash
~/bin/codexctl down
~/bin/codexctl up --dir ~/work/tmux --agents "fast,deep,test,sec" --noattach --unsafe
~/bin/codexctl attach
```

You can also make it the default:
```bash
export CODEXCTL_CODEX_ARGS="--dangerously-bypass-approvals-and-sandbox"
```

Back-compat: `CODEX_ARGS` is also honored if set.

## Troubleshooting
### `error connecting to /tmp/tmux-UID/default`
You ran a tmux command when no tmux server/session was running. Fix:
```bash
~/bin/codexctl up --dir ~/work/tmux --noattach
~/bin/codexctl attach
```

### Codex panes ask for login
Attach and finish auth once in each pane:
```bash
~/bin/codexctl attach
```

### Kill everything
```bash
~/bin/codexctl down
```
