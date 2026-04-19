# TodoScope — Demo Repository Specification

## Purpose

A curated repository designed to produce a clean, compelling Kanban board when scanned by TodoScope. This repo is used in presentations to guarantee a consistent, readable result every time.

## Repository Name

`todoscope-demo` (or `WEB-TodoScope-Demo`)

## Requirements

### The board must tell a story

When scanned, the Kanban board should show a believable project in active development — not a toy example, but not overwhelming either. The audience should be able to read the board in five seconds and understand the project's status.

### Target board state

| Column | Card Count | Purpose |
|--------|-----------|---------|
| Backlog | 2-3 | Shows future thinking, low-urgency notes |
| TODO | 3-4 | The main work queue — clear, actionable items |
| In Progress | 2 | Active work — suggests momentum |
| Bugs | 1 | One real bug — shows the system catches problems |
| Done | 3-4 | Proof of progress — things actually get finished |

**Total: 11-14 cards.** Enough to feel real. Few enough to read at a glance.

---

## Recommended Structure

```
todoscope-demo/
  README.md
  TODO.md
  src/
    app.py          # 2-3 inline TODOs
    auth.py         # 1 FIXME
    api.py          # 1 BUG, 1 TODO
    utils.py        # 1 NOTE
  tests/
    test_app.py     # 1 TODO
  .gitignore
  .todoscope-exclude.csv
```

### TODO.md

```markdown
# TODO

## In Progress

- Implement user dashboard with activity feed
- Refactor authentication to support OAuth providers

## Medium Priority

- Add CSV export for scan results
- Write onboarding guide for new contributors
- Set up CI pipeline for automated testing

## Bugs

- Rate limiter returns 500 instead of 429 on burst traffic

## Low Priority

- Evaluate WebSocket for real-time scan updates
- Add dark mode support

## Completed

- [x] Set up project structure and initial Flask app
- [x] Implement repository cloning and scanning
- [x] Add access key authentication
- [x] Create streaming results page with SSE
```

### Inline Comments (distributed across source files)

**src/app.py:**
```python
# TODO: Add pagination for repositories list when count exceeds 20
# TODO: Support scanning private repos with deploy keys
```

**src/auth.py:**
```python
# FIXME: Session timeout should be configurable, currently hardcoded to 24h
```

**src/api.py:**
```python
# BUG: API returns empty array instead of 404 when repo not found
# TODO: Add rate limiting per API key
```

**src/utils.py:**
```python
# NOTE: Git shallow clone saves ~60% bandwidth but loses blame history
```

**tests/test_app.py:**
```python
# TODO: Add integration tests for the streaming endpoint
```

---

## Board Preview

When scanned, the board should render approximately as:

```
| Backlog          | TODO              | In Progress         | Bugs               | Done                |
|------------------|-------------------|---------------------|---------------------|---------------------|
| Evaluate         | Add CSV export    | Implement user      | Rate limiter        | Set up project      |
| WebSocket for    |                   | dashboard with      | returns 500         | structure           |
| real-time updates| Write onboarding  | activity feed       | instead of 429      |                     |
|                  | guide             |                     |                     | Implement repo      |
| Add dark mode    |                   | Refactor auth to    | API returns empty   | cloning and         |
| support          | Set up CI pipeline| support OAuth       | array instead       | scanning            |
|                  |                   |                     | of 404              |                     |
| Git shallow      | Add pagination    | Session timeout     |                     | Add access key      |
| clone saves ~60% | for repo list     | should be           |                     | authentication      |
| bandwidth...     |                   | configurable        |                     |                     |
|                  | Support scanning  |                     |                     | Create streaming    |
|                  | private repos     |                     |                     | results page        |
|                  |                   |                     |                     |                     |
|                  | Add rate limiting |                     |                     |                     |
|                  | per API key       |                     |                     |                     |
|                  |                   |                     |                     |                     |
|                  | Add integration   |                     |                     |                     |
|                  | tests             |                     |                     |                     |
```

---

## Maintenance Notes

- Keep this repo stable. Don't add real development work to it.
- Review the board output before every presentation.
- If TodoScope's scanning logic changes, update the demo repo to match.
- The TODO.md content should feel like a real project, not lorem ipsum. Audience members will read the cards.
- Avoid in-jokes, placeholder text, or anything that requires explanation.
