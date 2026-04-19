# TodoScope — 15-Minute Walkthrough

## How This Extends the Keynote

The walkthrough adds five minutes to the keynote by expanding Beat 3 (The Product) into a hands-on guided experience. Beats 1, 2, 4, and 5 remain identical.

The additional time covers:

- **Installation walkthrough** (2 minutes)
- **Adding a local repo** (1 minute)
- **Kanban board deep-dive** (1 minute)
- **Live change detection** (1 minute)

---

## Extended Beat 3: The Product (0:45 – 11:45)

### 3a. Installation (0:45 – 2:45)

#### Script

"Let me show you how fast this is.

**Option one — Homebrew:**

```bash
brew install sage-is/apps/todoscope
todoscope
```

Two lines. You're running.

**Option two — Docker:**

```bash
docker pull ghcr.io/startr/todoscope
docker run -p 5000:5000 todoscope
```

**Option three — clone the repo:**

```bash
git clone https://github.com/Startr/WEB-MCPO-Repo_scanner.git
cd WEB-MCPO-Repo_scanner
make run
```

Every option gets you to the same place — localhost:5000, ready to scan."

#### Speaker Notes

- Show the Homebrew path first — it's the shortest.
- If presenting live, have all three options pre-loaded in terminal tabs. Don't type live unless you're confident.
- The point is speed, not thoroughness. Don't explain Docker to non-Docker people.

---

### 3b. First Scan — Curated Demo (2:45 – 6:45)

*Same as keynote Beat 3 — scan the curated demo repo, narrate the streaming results, land on the Kanban board.*

---

### 3c. Adding a Local Repo (6:45 – 7:45)

#### Script

"TodoScope doesn't just scan remote repos. You can point it at a project that already lives on your machine.

**[Click 'Add Local Repository' on the dashboard]**

I'll add a local project. Give it a path, give it a name. And here's what matters — that path never leaves this machine. It's never sent to the browser, never transmitted anywhere. Your code stays yours.

**[Click 'View TODOs' on the newly added local repo]**

Same scan. Same board. Same result. Whether it's a GitHub repo or a folder on your laptop, TodoScope treats it the same way."

#### Speaker Notes

- The security point — "path stays on this machine" — is worth emphasizing for self-hosted credibility.
- Have a local repo pre-registered as a backup in case adding one live has friction.

---

### 3d. Kanban Board Deep-Dive (7:45 – 8:45)

#### Script

"Let me walk you through how the board knows where to put things.

**[Point to each column]**

If you write `# TODO:` in your code — it goes in the TODO column. `# FIXME:` — In Progress, because a fix implies active work. `# BUG:` — Bugs. `# NOTE:` — Backlog, because notes are context, not action items.

And if you have a TODO.md file — which many projects do — TodoScope reads the sections. '## In Progress' maps to the In Progress column. '## High Priority' goes there too. A checked checkbox — `[x]` — goes to Done.

You don't learn a new system. You use the conventions you already use. TodoScope just reads them."

#### Speaker Notes

- This section is for the detail-oriented audience member who wants to understand the mapping.
- Keep it visual — point at the board, not at a slide.
- The punchline: "You use the conventions you already use." That's the cognitive accessibility argument landing in practice.
- Reference the guide panel built into the stream results page — it shows this mapping table.

---

### 3e. Live Change Detection (8:45 – 9:45)

#### Script

"One more thing. TodoScope doesn't just scan once and walk away. It watches.

**[Make a change to a TODO.md in the demo repo]**

I just added a new task to TODO.md. Watch the page.

**[Page detects the change, refreshes the TODO.md section]**

It picked it up. No rescan. No refresh. The board reflects reality in real time.

And if I push a new commit — 

**[Show the 'New changes detected' prompt]**

— it tells me something changed and offers a rescan. The board is always current."

#### Speaker Notes

- This is the "wow" moment for people who've maintained stale boards.
- Have the change pre-staged if you're worried about live typing speed.
- The emotional note: "The board is always current." That's the relief.

---

### 3f. Live Repo Scan (9:45 – 11:45)

*Same as keynote — scan an unrehearsed repo to prove it's real. In the walkthrough you have more time, so you can narrate what appears on the board and point out interesting findings.*

---

## Remaining Beats

Beats 4 and 5 proceed as written in the keynote script:

- **Beat 4: The Expansion** (11:45 – 12:45) — "Everyone sees it, even AI"
- **Beat 5: The Ecosystem** (12:45 – 14:30) — Sage.is AI UI, Sage.education, community
- **Close** (14:30 – 15:00) — "No extra work."

---

## Timing Summary (15-Minute Walkthrough)

| Section | Duration | Cumulative |
|---------|----------|------------|
| Opening line | 0:05 | 0:05 |
| Beat 1: The Problem | 0:25 | 0:30 |
| Beat 2: The Insight | 0:15 | 0:45 |
| Beat 3a: Installation | 2:00 | 2:45 |
| Beat 3b: Curated demo scan | 4:00 | 6:45 |
| Beat 3c: Local repo | 1:00 | 7:45 |
| Beat 3d: Kanban deep-dive | 1:00 | 8:45 |
| Beat 3e: Live change detection | 1:00 | 9:45 |
| Beat 3f: Live repo scan | 2:00 | 11:45 |
| Beat 4: The Expansion | 1:00 | 12:45 |
| Beat 5: The Ecosystem | 1:45 | 14:30 |
| Close | 0:30 | 15:00 |
