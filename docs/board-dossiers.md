# Board dossiers

Narration cut from open TODO.md cards during register passes. The board keeps
one short claim line per card; the full text and supporting evidence live here.

## MCPO / mpco naming (card: "MCPO: fix the transposed name…", Backlog)

Original card text (2026-08-15, pre-investigation):

> **MCP: implement or retire the name**: the brand audit established
> `/api/mpco` is a plugin-style manifest + OpenAPI REST surface, not the Model
> Context Protocol — user-facing copy now says "tool API". Decide the fork:
> build a real MCP server endpoint (JSON-RPC, tools/list, tools/call — then the
> MCP claim returns honestly) or retire the term project-wide (route names
> `/api/mpco/*` stay for compatibility either way). #ai #mcp #decision

Investigation findings (2026-08-15, prompted by Alexander flagging "MCPO —
that's an error"):

- The intended name is **MCPO**, not mpco. Evidence: the original GitHub repo
  was `Startr/WEB-MCPO-Repo_scanner`; the board's Completed list says
  "MCPo API for TODO files"; README's legacy TODO section says "our MCPo Api".
- The route namespace `/api/mpco/*` is a letter transposition (m-p-c-o vs
  m-c-p-o). It shipped transposed in the founding commit `eb67dac`
  (2025-05-22, "Add Dockerfile, Makefile, and TODO list; implement Flask
  app…") while the repo name in the same commit's README badge said MCPO.
  The typo is original — code and prose never agreed.
- Census 2026-08-15: `mpco` appears 14 times in `scanner/app.py` and in 11
  other files (templates: login 7, connect 10, index 3; docs: API_REFERENCE
  16, connect-sage 9, ARCHITECTURE, CONTRIBUTOR_GUIDE, DEVELOPMENT_WORKFLOW;
  README 6; CHANGELOG; TODO.md). The `mcpo`/`MCPo` spelling survives only in
  prose history (TODO.md Completed, README legacy section, old repo name).
- Context for the name: MCPO reads as "MCP-over-OpenAPI" — the same convention
  as the open-webui `mcpo` proxy (expose tools as OpenAPI for MCP-adjacent
  clients). The surface itself still does not speak the MCP wire protocol;
  the 2026-08-15 brand-audit relabel to "tool API" in user-facing copy stands
  regardless of the route spelling.

## Ralph-loop agent mode (card in Backlog)

Original card text:

> **Ralph-loop agent mode**: run an agent loop against TODO.md as the state
> file — each iteration picks the next unfinished item, works it, checks it
> off, commits. Fresh context per pass via `claude -p` in a bash loop (true
> Ralph) or `/loop` with `CLAUDE_CODE_AUTO_COMPACT_WINDOW` lowered to force
> frequent compaction (approximation). TODO.md is already the ideal Ralph
> state file. #ai #agent #automation

## Public local repos leak local_path (card in Bugs)

Original card text:

> **Public local repos leak `local_path`**: the scan-stream `init` payload
> sends the registered filesystem path to every viewer (it builds the
> vscode:// editor links), so a repo marked public shows the server's local
> path to anonymous visitors. Fix: only include `local_path` for authed
> sessions, or move editor-link building server-side. Found by the
> brand-audit honesty judge 2026-08-15. #security #privacy

Supporting detail: `scanner/app.py` adds `local_path` to the `init` SSE
payload for registered local repos; `stream_results.html` uses it to build
vscode:// / cursor:// / jetbrains:// editor URIs. `/stream_data/` is in
`_PUBLIC_REPO_PREFIXES`, so the public flag exposes the payload to anonymous
viewers. `docs/ARCHITECTURE.md` Security Notes describes the same behavior.
