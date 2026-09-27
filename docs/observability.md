# Observability bench

A way for the owner to watch the agents work — Claude Code, Codex and the decision
model — and answer three questions with data instead of impressions:

1. **Do they do what I asked?** Which tools each turn used, which subagents ran, what
   was delegated and what came back.
2. **Does the hand-off work?** A task followed from Claude to Codex and to the decision
   model, in one view.
3. **Where does the time go?** Model time, tool time, time waiting for a permission,
   time inside a delegation — so the slow part is the one optimised.

This is **not a harnex component**. Nothing here goes under `plugin/`, nothing is
written into a harnessed project, and no project needs it. It is configuration on the
owner's machine, enabled for this checkout, never committed. The backend is
[Langfuse](https://langfuse.com), run locally.

## Principles

- **Local configuration only.** Everything below lives in the owner's `~/`, in
  `~/langfuse`, or in this checkout's `.claude/`, which git ignores. Nothing is
  committed and no harnessed project is touched.
- **Keys never sit in a committed file.** The Langfuse secret key is held in the macOS
  Keychain by the Claude Code plugin that uses it.
- **Local Langfuse.** A self-hosted Langfuse on `localhost` keeps prompts and code on
  the machine, so full transcripts can be sent to it without a second thought.
- **Telemetry fails open.** An unreachable backend loses traces, never work. That is the
  opposite of the guard, and right here: this observes, it does not control.

## Stages

| # | Piece | Mechanism | When | Status |
|---|---|---|---|---|
| 0 | Langfuse | self-hosted with Docker Compose | now | **running** |
| 1 | Claude Code | Langfuse's Claude Code plugin, installed for this checkout only | now | **running** |
| 1b | Claude Code, finer timing | native OpenTelemetry traces (beta), user level | when stage 1 is not enough | optional |
| 2 | Codex | native OpenTelemetry traces, `[otel]` in `~/.codex/config.toml` | with S1 / C3, once Codex is driven through its plugin | pending |
| 3 | Decision model (Jev via OpenRouter) | OpenRouter *Broadcast* to Langfuse, no code | with C2, once `decide.py` exists | pending |
| 4 | One view across the three | shared session id and trace context | after 2 and 3 | pending — needs two small harnex facts, below |

### 0 · Langfuse, locally

```bash
git clone https://github.com/langfuse/langfuse.git ~/langfuse
```

Before the first start, add `~/langfuse/docker-compose.override.yml`. Compose merges it
with the upstream file, which stays untouched and can be pulled freely:

```yaml
# Postgres is only reached inside the compose network, so its port is not published
# (5432 is often taken on the host). Web and MinIO listen on localhost only.
services:
  postgres:
    ports: !reset []
  langfuse-web:
    ports: !override
      - 127.0.0.1:3000:3000
  minio:
    ports: !override
      - 127.0.0.1:9090:9000
      - 127.0.0.1:9091:9001
```

Without it, a host that already runs a Postgres on 5432 fails with *Bind for
0.0.0.0:5432 failed: port is already allocated*, and a second `up` leaves the web
container looping on *P1001: Can't reach database server at `postgres:5432`*. The
upstream defaults also publish the web UI and MinIO on every interface, with the
`CHANGEME` secrets of the compose file; the override keeps them on `localhost`.

```bash
cd ~/langfuse && docker compose up -d
```

Open `http://localhost:3000`, create an account (it is local), an organisation and a
project, and in the project's *Settings → API Keys* a key pair. Langfuse shows it as
three env-file lines — `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`,
`LANGFUSE_BASE_URL` — and suggests pasting a prompt that installs a Langfuse skill "to
add tracing to this application". Ignore the prompt: it instruments an application's
own LLM calls with the Langfuse SDK, which is not what is observed here, and would put a
dependency and a technology name where the plan forbids them (decision 15, and
technologies only in `plugin/tools/profiles/`). The three values are for the plugin
below.

The containers are `restart: always`; they come back when Docker starts.

### 1 · Claude Code → Langfuse, for this checkout

Langfuse's Claude Code plugin registers a Stop hook that, after every answer, reads
the session transcript and sends it to Langfuse: one trace per turn, with a span per
model message and per tool call, grouped by session. It runs as a `uv` script, so the
SDK it needs never touches the machine's Python. It works in the terminal and in the
desktop app's Code tab.

**Steps**

1. Register the marketplace, once per machine:
   ```bash
   claude plugin marketplace add langfuse/Claude-Observability-Plugin
   ```
2. Install the plugin for this checkout only. `--scope local` records it in
   `.claude/settings.local.json`, which git ignores:
   ```bash
   claude plugin install langfuse-observability@langfuse-observability --scope local
   ```
3. Give it the three values, when the install asks or later from an interactive
   `claude` session with `/plugin configure langfuse-observability@langfuse-observability`.
   Do not pass them with `--config`: the secret would land in the shell history.
   - `LANGFUSE_PUBLIC_KEY` — the `pk-lf-…` key.
   - `LANGFUSE_SECRET_KEY` — the `sk-lf-…` key; the plugin keeps it in the Keychain.
   - `LANGFUSE_BASE_URL` — `http://localhost:3000`. Left empty, the plugin sends to
     Langfuse Cloud (EU) instead.
4. Start a new Claude Code session in the checkout; a running one does not load the
   plugin.

**Check**

1. `claude plugin list` shows `langfuse-observability`, scope `local`, enabled.
2. Ask something that uses a tool (`list the files in docs`).
3. When the answer ends, Langfuse → *Tracing* shows the turn, with its model messages
   and tool calls inside.
4. If nothing arrives: `docker compose ps` in `~/langfuse`; the base URL has no
   trailing slash; `uv --version` answers.

**Verified against:** Claude Code 2.1.267, Langfuse 4.46.0, plugin
`langfuse-observability` 1.2.0 — 2026-09-27.

**What it does not show.** The plugin rebuilds each turn from the transcript after the
fact, so it cannot tell time spent waiting for a permission from time spent working.
Stage 1b can.

### 1b · Claude Code, native traces (optional)

Claude Code exports its own OpenTelemetry traces (beta): one `claude_code.interaction`
per prompt, with `claude_code.llm_request` (model, tokens, stop reason) and
`claude_code.tool` split into `tool.blocked_on_user` and `tool.execution`, plus
subagents. That split is the one stage 1 lacks.

It can only be switched on at **user level**: Claude Code ignores the OpenTelemetry
exporter variables in a repository's `.claude/settings.json` and
`.claude/settings.local.json`. So it applies to every project on the machine. If it is
wanted:

1. Keys in the Keychain, each command prompting for its value:
   ```bash
   security add-generic-password -a "$USER" -s langfuse-public-key -w
   security add-generic-password -a "$USER" -s langfuse-secret-key -w
   ```
2. A header helper at `~/.claude/langfuse-otel-headers.sh`, executable, run once by
   hand to grant it Keychain access (*Always Allow*):
   ```sh
   #!/bin/sh
   # Prints the OTLP headers Langfuse expects, reading the keys from the Keychain.
   pk=$(security find-generic-password -a "$USER" -s langfuse-public-key -w) || exit 1
   sk=$(security find-generic-password -a "$USER" -s langfuse-secret-key -w) || exit 1
   auth=$(printf '%s:%s' "$pk" "$sk" | base64 | tr -d '\n')
   printf '{"Authorization":"Basic %s","x-langfuse-ingestion-version":"4"}\n' "$auth"
   ```
3. In `~/.claude/settings.json`, merged with what is there (absolute path, no `~`):
   ```json
   {
     "otelHeadersHelper": "/Users/<you>/.claude/langfuse-otel-headers.sh",
     "env": {
       "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
       "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA": "1",
       "OTEL_TRACES_EXPORTER": "otlp",
       "OTEL_EXPORTER_OTLP_TRACES_PROTOCOL": "http/protobuf",
       "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT": "http://localhost:3000/api/public/otel/v1/traces",
       "OTEL_METRICS_EXPORTER": "none",
       "OTEL_LOGS_EXPORTER": "none",
       "OTEL_LOG_USER_PROMPTS": "1",
       "OTEL_LOG_TOOL_DETAILS": "1"
     }
   }
   ```
   `http/protobuf` because Langfuse takes OTLP over HTTP only and Claude Code defaults
   to gRPC (the header helper also works only over HTTP); the endpoint is the full
   per-signal path; metrics and logs are off because Langfuse ingests traces only.
4. Restart Claude Code. To debug, set `OTEL_TRACES_EXPORTER` to `console`: spans
   printed means the problem is the endpoint or the headers.

With both 1 and 1b on, each turn appears twice in Langfuse; turn the plugin off for the
checkout (`claude plugin disable langfuse-observability@langfuse-observability --scope local`)
when 1b takes over.

### 2 · Codex → Langfuse (pending)

Codex exports OpenTelemetry traces when `~/.codex/config.toml` has a trace exporter
table, `[otel.trace_exporter.otlp-http]`, pointing at the same Langfuse endpoint with
the same two headers. Codex takes static headers, so the Basic string has to be written
in that file or produced by a wrapper; decide which when this stage starts.

Open before starting: [openai/codex#12913](https://github.com/openai/codex/issues/12913)
reports that `codex exec` emits no metrics and `codex mcp-server` no telemetry at all.
Find out which entry point the Codex plugin uses (`/codex:rescue`) and whether it
exports traces — part of the S1 spike's evidence.

### 3 · Decision model → Langfuse (pending)

The decision model runs on OpenRouter, whose *Broadcast* feature (Settings →
Observability) sends every request to Langfuse with no code: base URL and keys go in the
OpenRouter dashboard. A request's `session_id` becomes the Langfuse session, and extra
`trace` keys become metadata. A local Langfuse is not reachable from OpenRouter; this
stage needs a hosted Langfuse or a tunnel, and decides between them when it starts.

### 4 · One view across the three (pending)

Each piece sends its own traces; seeing one task cross all three needs a shared id.
Two facts belong to harnex and are recorded here until their phases arrive:

- **S1 question:** Claude Code passes `TRACEPARENT` to the processes its Bash tool
  starts (with native traces on, stage 1b). Does Codex, started through its plugin,
  honour it as the parent of its own spans?
- **C2 requirement:** `decide.py` forwards the Claude Code session id (and, when
  present, `TRACEPARENT`) with each OpenRouter request as `session_id` and trace
  metadata. It names no backend: it passes on ids that already exist, and costs nothing
  when no one is listening.

## What to look at

Questions to ask Langfuse once traces arrive:

- Which share of a turn is model time and which is tool time (and, with 1b, how much is
  `blocked_on_user`)?
- Which tools are slowest, and which are called repeatedly with the same input?
- How many model calls does a typical task take, and how many input tokens each — is
  context growing faster than the work?
- Which subagents run, how long they take, and whether their result is used.

## Sources

- [Langfuse — Claude Code integration](https://langfuse.com/integrations/other/claude-code)
- [Langfuse — Claude Code plugin](https://github.com/langfuse/Claude-Observability-Plugin)
- [Langfuse — self-hosting](https://langfuse.com/self-hosting)
- [Langfuse — OpenTelemetry](https://langfuse.com/integrations/native/opentelemetry)
- [Claude Code — monitoring usage](https://code.claude.com/docs/en/monitoring-usage)
- [Codex — advanced configuration](https://developers.openai.com/codex/config-advanced)
- [OpenRouter — Broadcast to Langfuse](https://openrouter.ai/docs/guides/features/broadcast/langfuse)
