RFC: tmux Control Channel for Sub-Agent CLIs
===========================================

Status
------
- Status: Draft (aligned to codexctl v2 implementation)
- Owner: platform agents
- Target: Any LLM session driving another CLI-based agent (e.g., Codex) through tmux

Context
-------
We often use tmux to host a "controller" pane and one or more sub-agent panes running an LLM CLI. This document defines a safe, repeatable protocol for sending prompts, submitting them, and harvesting output so we do not mis-trigger the sub-agent (e.g., by submitting the wrong prefilled prompt).

Scope and Assumptions
---------------------
- You are using `codexctl` v2, which creates and manages its own tmux session and window for agents.
- Pane target examples use `%1`; adjust for your layout.
- The sub-agent CLI (Codex) pre-fills its prompt (e.g., "Write tests for @filename") and only submits when it receives a real Enter key. Carriage returns (C-m) or linefeeds (C-j) sent via `tmux send-keys` do not submit.
- `tmux capture-pane` is available for readback.
- Model selection is fixed when each pane is started. Routing picks the *pane* (agent), not the model.
- Reasoning effort flags are not automatically validated by `codexctl`.

Model and Effort (codexctl v2)
------------------------------
- Per-agent model/profile selection happens at *pane start* using `codexctl up --profiles ... --models ...`.
- `codexctl route` chooses a named agent (fast/deep/test/sec) based on keywords/length; it does **not** change a model.
- If you need to override reasoning effort, pass it via Codex CLI config flags when launching panes (out of scope for codexctl).

Protocol Overview
-----------------
1) Create/attach sub-agent panes (codexctl-managed session)
   - `codexctl up` creates a dedicated tmux session + window and spawns sub-agent panes there.
   - Do not manually split panes inside that session unless you also update mappings.

2) Identify the target pane id
   - Use `codexctl ids` or `tmux list-panes` and note the pane id for the target sub-agent.

3) Observe without mutation
   - `tmux capture-pane -p -t <id>`

4) Submit a prompt (safe pattern, codexctl behavior)
   - Clear the input line to avoid submitting the prefill:
     - `tmux send-keys -t <id> Home C-k`
   - Type the prompt literally (no key interpretation) and submit Enter as its own send-keys.
   - codexctl does this internally via multiple tmux calls (same effective behavior as a single shell block).

5) Poll for state and completion
   - codexctl prefixes prompts with `[JOB:<id>]` (unless `--nojob` is used).
   - When `--wait` is enabled, it polls scrollback and treats completion as:
     - the presence of the `[JOB:<id>]` line, followed by a `Worked for ...` banner **after** it.

6) Read back output
   - `tmux capture-pane -p -t <id>` (optionally with `-S` to limit scrollback)

Observed run (pane %2 example)
------------------------------
- Discovered panes with `codexctl ids` and targeted the Codex pane `%2`.
- Cleared the prefill with `Home C-k`, sent `Test prompt: say hello from Codex in this pane.` using `-l`, then a separate `Enter`.
- Saw `─ Worked for 6s ──` and the response `Hello from Codex in this pane!`, then the prompt returned to idle.

Critical Behaviors to Remember
------------------------------
- Do NOT rely on `C-m` or `C-j` to submit; they only insert newlines for Codex. A separate `tmux send-keys ... Enter` is required.
- If you use `tmux send-keys -l ... Enter` in one call, the word "Enter" will be typed literally because `-l` forces literal characters. Keep Enter in its own call.
- The CLI prefill is live: hitting Enter on an empty line will submit whatever is preloaded (e.g., `Write tests for @filename`). Always clear before sending.
- `C-u` may not clear the Codex input buffer. Use `Home C-k` to remove the line reliably.
- Completion detection in codexctl uses `[JOB:<id>]` and a subsequent `Worked for ...` banner when `--wait` is used.
- When a multi-part command is sent and captured immediately, scrollback may include prior runs; watch the most recent prompt at the bottom to confirm what was actually submitted.

Common Tasks
------------
- Check pane IDs: `codexctl ids` or `tmux list-panes`
- Send multi-line content: send one line at a time with separate `-l` calls, then a final Enter.
- Interrupt a hanging request: send `tmux send-keys -t <id> C-c` (if the sub-agent supports it) or restart the pane.

Example One-Liner (submit + captures, single shell call)
-------------------------------------------------------
```
{ tmux send-keys -t <id> Home C-k; \
  tmux send-keys -t <id> -l "Summarize the current backlog and risks."; \
  sleep 0.1; \
  tmux send-keys -t <id> Enter; \
  tmux capture-pane -p -t <id>; \
  sleep 0.2; tmux capture-pane -p -t <id>; \
  sleep 0.5; tmux capture-pane -p -t <id>; \
  sleep 1;   tmux capture-pane -p -t <id>; \
  sleep 5;   tmux capture-pane -p -t <id>; }
```

Operational Checklist
---------------------
- [ ] Confirm target pane id via `codexctl ids` (do not assume `%1`).
- [ ] Clear the prefilled prompt (`Home C-k`).
- [ ] Send prompt with `-l`.
- [ ] Submit with separate Enter.
- [ ] Poll captures until you either see `Working` (in progress) or a `Worked for ...` banner (complete).
- [ ] Review bottom-most prompt/output to confirm the request that actually ran.

Appendix: codexctl v2 specifics
-------------------------------
- codexctl maintains agent mappings in tmux session options:
  - `@codexctl_agents` and `@codexctl_pane_<name>`
- Routing (`codexctl route`) chooses an agent based on prompt heuristics. It does not change models.
- Models/profiles are fixed at pane creation time using `codexctl up --profiles/--models`.

Unsafe mode (bypass approvals/sandbox)
--------------------------------------
If you launch Codex panes with `--dangerously-bypass-approvals-and-sandbox` (sometimes exposed via `codexctl up --unsafe` or environment args),
the agent may execute actions without interactive approvals.

Guidance:
- Use only in a dedicated sandbox environment (container/VM) with limited permissions.
- Prefer normal mode for day-to-day work; keep `--unsafe` for tightly scoped, time-boxed tasks.
- If enabling by environment variable, prefer `CODEXCTL_CODEX_ARGS` and treat legacy `CODEX_ARGS` as back-compat only.
