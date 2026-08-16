# API Reference

All routes are served by the Flask app in `scanner/app.py`.

## Base URL

```text
http://localhost:5000
```

Default port is 5000. The CLI (`todoscope`) auto-picks the next free port if 5000
is taken; `--exact-port` makes it bind exactly `--port` or fail. Tool-API routes
live under `/api/mcpo/`.

Naming note: the `/api/mcpo/*` surface is a plugin-style manifest + OpenAPI REST API. It is not the Model Context Protocol. The namespace was renamed on 2026-08-15 from the founding-commit typo `mpco` — a clean break, the old paths are gone. In prose call it the "tool API".

## Authentication

Auth is driven by `access_keys.csv` — `$TODOSCOPE_DATA_DIR/access_keys.csv`
(the CLI sets `TODOSCOPE_DATA_DIR` to `~/.todoscope/`), or
`scanner/access_keys.csv` in dev. Columns: `key,label`. **No file, or no keys in
it, means auth is disabled — every route is open.** Once at least one key
exists, every route requires a key except the public ones listed below.

Three ways to present a key:

| Mechanism | How | Use for |
| --- | --- | --- |
| Session | `POST /login` with form fields `key` and optional `remember` | Browsers. `remember` makes the session permanent (30-day lifetime) |
| Query param | `?key=<key>` on any request | Shareable links, badges behind auth |
| Bearer header | `Authorization: Bearer <key>` | API clients, curl, agents |

Session cookies are signed with `SECRET_KEY` env if set, else a generated key
persisted at `~/.todoscope/.secret_key` (mode 0600), else a per-process random
key.

Unauthenticated requests: clients that accept JSON but not HTML get
`401` with `{"error": "Valid access key required", "hint": "Pass ?key=<your-key> or Authorization: Bearer <key>"}`;
browsers get a `302` redirect to `/login?next=<url>`.

### Always-public routes

- `/health`, `/login`, `/resources`, `/api/mcpo/manifest`, `/api/mcpo/openapi.json`
- `/static/*`
- `/api/badge/todos/*` (count only, no code content)
- `/api/webhook/*` (does its own HMAC verification instead)

### Public-repo routes

Repos flagged public (dashboard toggle, `POST /toggle_public/<repo>`) expose
these read-only prefixes without a key: `/scan_stream/`, `/stream_data/`,
`/events/`, `/api/repo_fingerprint/`, `/api/todo_files/`.

## Health Check

### `GET /health`

Public. No side effects. Readiness probe for the desktop shell; `auth` tells the
shell whether an access key exists (so it can refuse network sharing when none
does).

```bash
curl http://localhost:5000/health
```

```json
{"status": "ok", "app": "todoscope", "version": "1.0.0", "auth": true}
```

## Web Routes (summary)

HTML pages and form handlers. Auth applies unless marked public.

| Route | Method | Purpose |
| --- | --- | --- |
| `/` | GET, POST | Dashboard. POST takes `repo_url` (git URL **or** local path — paths starting with `/`, `~`, `.` register as local repos), optional `shallow` checkbox; redirects to `/scan_stream/<repo>` |
| `/connect` | GET | Step-by-step guide for pointing an AI agent at this server |
| `/login` | GET, POST | Login form. POST fields: `key`, `remember`. Public |
| `/logout` | GET | Clear session, redirect to `/login` |
| `/setup/add_key` | POST | Bootstrap flow: write first key to `access_keys.csv`. `403` once auth is configured |
| `/add_local` | POST | Register a local repo path (`local_path`, `display_name`). Paths stay server-side; the web sees display names only |
| `/remove_local/<repo>` | GET | Unregister a local repo (mapping only, never deletes files) |
| `/remove_repo/<repo>` | POST | Unregister local repo, or delete a cloned repo's directory |
| `/toggle_public/<repo>` | POST | Flip the repo's public flag |
| `/webhook_secret/<repo>` | POST | Generate or remove a webhook secret (`action=generate\|remove`). `404` if repo unknown |
| `/pull/<repo>` | GET | `git pull`, then redirect to `/scan_stream/<repo>` |
| `/scan/<repo_url>` | GET | Legacy — redirects to `/scan_stream/<repo_url>` |
| `/scan_stream/<repo_url>` | GET | The scan/board page. Query: `shallow=1`, `refresh=1` |
| `/resources` | GET | Curated Kanban resources. Public |

## Streaming Routes

### `GET /stream_data/<repo_url>`

Server-sent events feeding the scan page. `repo_url` is a git URL or a
registered repo name. Query params: `shallow=1` (depth-1 clone), `refresh=1`
(ignore the incremental cache, force a full rescan).

Scans are incremental: per-repo state in `scan_state/<repo>.json` records
`last_head`, an exclusions hash, cached todos, and blame. Only files changed
since the last scanned HEAD are re-parsed; when nothing changed, cached
results are served without a scan.

Event types (`data:` lines, JSON):

| `type` | Payload |
| --- | --- |
| `init` | `repo_name`, `repo_url`, `branch`, `host_kind`, `host`, `owner`, `repo`, `web_file_url_template` (file-view URL with `{path}`/`{line}` placeholders; GitHub maps to vscode.dev, GitLab/Gitea/Codeberg/Bitbucket/sourcehut to their file views; `null` for unknown hosts), `local_path` (local repos only) |
| `status` | `message` — progress text |
| `todo_md_files` | `count`, `html` fragment |
| `todos_list` | `count`, `html` fragment (full list) |
| `todo` | `count`, `html` fragment (one item, full-scan path only) |
| `kanban` | `html` fragment; may arrive twice (pre- and post-blame), plus an instant stale board from the cached canvas |
| `excluded` | `items` — paths skipped via `.todoscope-exclude.csv` |
| `complete` | `count`, `repo_name`, `source` (`local` or `cloned`) |
| `error` | `message` |

### `GET /events/<repo_name>`

Persistent SSE live channel. Subscribing starts a watcher — a watchdog
filesystem observer for local repos (2s fingerprint poll fallback), a 60s git
poll for clones. On change the server rescans incrementally and pushes fresh
`kanban`, `todo_md_files`, and `todos_list` fragments (same shapes as above);
the client morphs them in with idiomorph. Comment heartbeats (`: ping`) are sent every
15s of idle to keep proxies from closing the stream. `404`
`{"error": "Unknown repository"}` for unknown repos.

```bash
curl -N http://localhost:5000/events/my-repo -H "Authorization: Bearer <key>"
```

## JSON API Routes

### `GET /api/badge/todos/<repo_name>`

Public. shields.io endpoint-badge JSON — live TODO count.

```text
https://img.shields.io/endpoint?url=https://YOUR_HOST/api/badge/todos/<repo_name>
```

```json
{"schemaVersion": 1, "label": "TODOs", "message": "12", "color": "orange"}
```

Colors: 0 → `brightgreen`, <10 → `yellow`, <50 → `orange`, else `red`. Unknown
repo or scan error returns `200` with message `repo not found` / `error` and
`lightgrey`.

### `GET /api/repo_fingerprint/<repo_name>`

Lightweight change detection: short HEAD sha, working-tree dirty flag, and an
8-char md5 of TODO-file content.

```json
{"fingerprint": "0b96df6", "dirty": true, "todo_hash": "a3f9c2e1"}
```

Unknown repo returns `200` with `{"fingerprint": "", "dirty": false}` — no
`todo_hash` key. The internal-error path returns all three keys empty.

### `GET /api/todo_files/<repo_name>`

TODO.md/TODO.txt content only — no code scan.

```json
{"files": [{"file_path": "TODO.md", "content": "# TODO\n..."}]}
```

### `POST /api/todo_toggle/<repo_name>`

Flip a task checkbox in a TODO file — write-back from the web UI. **Registered
local repos only** (the file is the real working copy).

Request:

```json
{"file_path": "TODO.md", "line_num": 12, "line_hash": "9f2ab41c", "checked": true}
```

`line_hash` is the first 8 hex chars of the md5 of the right-stripped line as it
was rendered (the server embeds it in each checkbox fragment). The server
recomputes the hash of the current line; a mismatch means the line changed since
render, and the write is refused — a stale view can never clobber an editor
save. The next live morph shows the viewer reality.

Success:

```json
{"ok": true, "line": 12, "checked": true}
```

Errors:

| Status | Body | Cause |
| --- | --- | --- |
| 403 | `{"error": "Write-back is only available for registered local repositories"}` | Repo not registered local |
| 400 | `{"error": "Invalid path"}` | Path escapes the repo |
| 400 | `{"error": "Not a TODO file"}` | Target is not `todo.md`/`todo.txt` |
| 404 | `{"error": "Cannot read file: ..."}` | File unreadable |
| 409 | `{"error": "Line out of range"}` | `line_num` outside the file |
| 409 | `{"error": "Line changed since render"}` | Hash mismatch — stale view |
| 409 | `{"error": "Not a task line"}` | Line is not a Markdown task item (`-`/`*`/`+` bullet followed by `[ ]`/`[x]`) |

The write itself triggers the watchdog, which rescans and pushes fresh fragments
to every `/events/` subscriber.

### `POST /api/webhook/<repo_name>`

Push-event webhook for GitHub/GitLab (or anything that can send a header).
Exempt from key auth — verified against the repo's webhook secret instead
(generate one via `POST /webhook_secret/<repo>`; it appears in the dashboard).

Verification — any one of:

| Provider | Header | Check |
| --- | --- | --- |
| GitHub | `X-Hub-Signature-256: sha256=<hex>` | HMAC-SHA256 of the raw request body with the secret |
| GitLab | `X-Gitlab-Token: <secret>` | Constant-time equality |
| Generic | `Authorization: Bearer <secret>` | Constant-time equality |

On success: pull, rebuild KANBAN.canvas, push fresh fragments to live
subscribers.

```json
{"ok": true, "pull": "Successfully pulled latest changes", "cards": 42}
```

Errors:

| Status | Body | Cause |
| --- | --- | --- |
| 404 | `{"error": "No webhook configured for this repo"}` | No secret set |
| 403 | `{"error": "Invalid signature"}` | No header verified |
| 429 | `{"error": "Rate limited", "retry_after": 21}` | <30s since last trigger for this repo |
| 404 | `{"error": "Repo not found"}` | Secret exists but path unresolvable |

Rate limit is in-memory, per repo, 30s minimum between triggers.

```bash
# GitHub-style
BODY='{"ref":"refs/heads/master"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')
curl -X POST http://localhost:5000/api/webhook/my-repo \
  -H "X-Hub-Signature-256: sha256=$SIG" \
  -H "Content-Type: application/json" -d "$BODY"
```

## Tool API (`/api/mcpo/*`)

Manifest + OpenAPI REST surface for AI agents. `manifest` and `openapi.json` are
public so agents can discover the API; the tool endpoints themselves require a
key when auth is enabled (Bearer or `?key=`).

Tool endpoints wrap responses:

```json
{"status": "success", "result": { ... }}
```

```json
{"status": "error", "error": "message"}
```

Errors return `500` with that shape.

### `GET /api/mcpo/manifest`

Public. Plugin-style manifest.

```json
{
  "schema_version": "v1",
  "name_for_human": "TodoScope",
  "name_for_model": "todo_scanner",
  "description_for_human": "Scans git repositories for TODO comments in code",
  "description_for_model": "Use this tool to scan git repositories for TODO comments. ...",
  "authentication": {"type": "none"},
  "api": {"type": "openapi", "url": "http://localhost:5000/api/mcpo/openapi.json"}
}
```

### `GET /api/mcpo/openapi.json`

Public. OpenAPI 3.0.1 spec for the four tool endpoints, with request/response
schemas. Server URL is derived from the request origin.

### `POST /api/mcpo/scan_repository`

Clone (or reuse) a repo, scan it, build KANBAN.canvas, return everything.

Request:

```json
{"repo_url": "https://github.com/user/repo.git", "shallow": true}
```

`repo_url` may also be a registered repo name. `shallow` (optional, default
false) does a `--depth 1` clone. Existing clones auto-pull when older than 5
minutes.

Response `result`:

```json
{
  "repo_url": "https://github.com/user/repo.git",
  "repo_name": "repo",
  "todo_count": 2,
  "todos": [
    {"file_path": "src/main.py", "line_num": 42,
     "todo_text": "# TODO: Implement error handling",
     "next_line": "def process_data():"}
  ],
  "todo_md_files": [{"file_path": "TODO.md", "content": "# TODO\n..."}],
  "excluded": [],
  "web_url": "http://localhost:5000/scan/https://github.com/user/repo.git",
  "kanban_canvas": {"nodes": [], "edges": []}
}
```

### `GET /api/mcpo/list_repositories`

All repos — registered local and cloned. Never exposes filesystem paths.

Response `result`:

```json
{
  "repositories": [
    {"name": "repo", "last_modified": "2026-08-15 11:30:00",
     "origin_url": "https://github.com/user/repo.git",
     "scan_url": "http://localhost:5000/scan/repo"}
  ],
  "count": 1
}
```

### `POST /api/mcpo/pull_repository`

`git pull` a **cloned** repo by name (looked up under the clone directory, not
the local-repo registry).

Request:

```json
{"repo_name": "repo"}
```

Response `result`:

```json
{
  "success": true,
  "message": "Successfully pulled latest changes",
  "details": "Already up to date.",
  "repo_name": "repo",
  "origin_url": "https://github.com/user/repo.git",
  "last_modified": "2026-08-15 11:30:00",
  "scan_url": "http://localhost:5000/scan/repo"
}
```

### `POST /api/mcpo/scan_repository_stream`

Streaming scan — newline-delimited JSON (`application/x-ndjson`), one object per
line. Request body same as `scan_repository`. `400`
`{"status": "error", "error": "Repository URL is required"}` if `repo_url` is
missing.

```json
{"type": "init", "status": "success", "repo_name": "repo", "repo_url": "...", "web_url": "..."}
{"type": "todo_md_files", "status": "success", "files": [...]}
{"type": "todo", "status": "success", "todo": {...}, "count": 1}
{"type": "excluded", "status": "success", "items": [...]}
{"type": "kanban", "status": "success", "canvas": {...}}
{"type": "complete", "status": "success", "count": 1, "repo_name": "repo", "repo_url": "...", "web_url": "..."}
```

On failure the stream ends with
`{"type": "error", "status": "error", "error": "...", "error_id": "..."}`.

## Error Code Reference

| Status | Routes | Meaning |
| --- | --- | --- |
| 400 | `/api/todo_toggle` | Path escapes repo, or target is not a TODO file |
| 400 | `/api/mcpo/scan_repository_stream` | Missing `repo_url` |
| 401 | Any protected route | No valid key (JSON clients). Browsers get 302 → `/login` |
| 403 | `/api/webhook` | Signature/token failed verification |
| 403 | `/api/todo_toggle` | Repo is not a registered local repo |
| 403 | `/setup/add_key` | Auth already configured — edit `access_keys.csv` directly |
| 404 | `/events`, `/webhook_secret`, `/api/webhook` | Unknown repo / no webhook secret |
| 404 | `/api/todo_toggle` | TODO file unreadable |
| 409 | `/api/todo_toggle` | Stale line hash, line out of range, or not a task line |
| 429 | `/api/webhook` | Rate limited — 30s per repo; body carries `retry_after` seconds |
| 500 | `/api/mcpo/*` | `{"status": "error", "error": "..."}` |
| 500 | Other `/api/*` on internal `ScannerError` | `{"status": "error", "error_id", "message", "category", "recoverable"}` |

`/api/badge/todos`, `/api/repo_fingerprint`, and `/api/todo_files` return `200`
with empty/placeholder payloads for unknown repos rather than erroring.

## Usage Examples

```bash
# Scan a repository
curl -X POST http://localhost:5000/api/mcpo/scan_repository \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/user/repo.git", "shallow": true}'

# List repositories
curl -H "Authorization: Bearer $KEY" \
  http://localhost:5000/api/mcpo/list_repositories

# Toggle a checkbox
curl -X POST http://localhost:5000/api/todo_toggle/my-repo \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "TODO.md", "line_num": 12, "line_hash": "9f2ab41c", "checked": true}'
```

```python
import requests

r = requests.post(
    "http://localhost:5000/api/mcpo/scan_repository",
    headers={"Authorization": "Bearer YOUR_KEY"},
    json={"repo_url": "https://github.com/user/repo.git"},
)
data = r.json()
if data["status"] == "success":
    for todo in data["result"]["todos"]:
        print(f'{todo["file_path"]}:{todo["line_num"]}  {todo["todo_text"]}')
else:
    print("Error:", data["error"])
```
