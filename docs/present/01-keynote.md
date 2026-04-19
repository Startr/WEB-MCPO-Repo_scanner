# TodoScope — 10-Minute Keynote

## Opening Line

> "Collaboration can be complicated, but it doesn't have to be."

---

## Beat 1: The Problem (0:00 – 0:30)

### Script

"Every team I've ever worked with has the same problem. You start a project, you pick a tracking tool — Jira, Trello, Linear, a spreadsheet — and for the first two weeks it's beautiful. Everything's up to date. Everyone knows what's happening.

Then life happens. People stop updating the board. Tickets go stale. And the only person who actually knows what's unfinished... is the one person who can hold it all in their head."

### Speaker Notes

- Deliver conversationally. This isn't a complaint instead it's a shared experience.
- Let the audience nod. They've lived this.
- Don't name-drop competitors with malice. The problem isn't the tools; it's that all tools require extra work.

---

## Beat 2: The Insight (0:30 – 0:45)

### Script

"It doesn't have to be this way your project already knows what's unfinished. Every TODO comment, every FIXME, every BUG tag, every task in your TODO.md — it's all right there. In the repo. Being ignored by every project management tool you've worked with.

What if you didn't have to maintain a separate system at all?"

### Speaker Notes

- This is the reframe. Land it and pause.
- The question at the end is rhetorical — don't rush past it.
- One beat of silence before transitioning to the demo.

---

## Beat 3: The Product (0:45 – 6:45)

### Script

"This is TodoScope."

**[Live demo begins — scan the curated demo repo]**

"I'm going to point it at a repository and let you watch."

**[Initiate scan — results stream in real time]**

"What you're seeing right now is TodoScope reading the repo. Every file. Every comment. Every TODO.md. And as it finds things - watch — they appear in real time."

**[TODOs stream in]**

"There's a TODO here in the authentication module. A FIXME in the API handler. A BUG tag someone left six weeks ago. A NOTE about a design decision."

**[Kanban board assembles]**

"And now: here's the board. Five columns. Backlog. TODO. In Progress. Bugs. Done. Built entirely from what was already in the code. Nobody moved a card. Nobody updated a ticket. The board built itself."

**[Pause — let the board sit on screen]**

"That board will never go stale. Because it's not a copy of the truth — it IS the truth. You update your code, the board updates. There's no extra work."

**[Brief pause — then address the elephant]**

"Now — there are great tools that scan code for TODOs. Todo Tree, leasot — solid tools. There are extensions that render kanban boards from markdown. But none of them put it all together — scan your code, parse your TODO.md, build the board, and expose it to your AI teammates — with zero configuration and zero extra work. And none of them are open source."

**[If doing live keynote — scan a second, real repo]**

"And just to prove this isn't a magic trick — let me point it at something I haven't rehearsed."

**[Scan a real repo. Let the audience see it build live.]**

"Different repo. Same result. The board builds itself."

### Speaker Notes

- This is six minutes. Let the demo breathe.
- Resist the urge to narrate every TODO that appears. Pick three or four that tell a story.
- The Kanban board assembling is the climax of this beat. Let it land visually before you speak over it.
- The competitive acknowledgment is generous, not defensive. You're crediting the ecosystem and showing you know it. The differentiator lands harder because you earned it honestly.
- If someone asks about Imdone specifically: "Imdone is solid — it's a paid desktop app that does kanban from code comments. TodoScope is open source, web-accessible, and built for AI agents. Different tools for different needs."
- When scanning the live repo, don't apologize for what's on the board. Realness is the point.
- If something unexpected shows up, lean into it: "See? That's a real TODO someone left. And now everyone can see it."

### Demo Sequence (Curated Repo)

1. Open TodoScope dashboard (already logged in)
2. Enter demo repo URL
3. Click "Scan Repository"
4. Streaming results page loads — TODOs appear one by one
5. TODO.md content surfaces with rendered markdown
6. Kanban board assembles — five columns, color-coded
7. Pause on the board. Point out the column structure.
8. Click a code.dev link to show the TODO in context

---

## Beat 4: The Expansion (7:00 – 8:00)

### Script

"So now your whole team can see what needs doing. The developer who just joined this morning doesn't have to wait for a briefing — they open the board. The project manager doesn't have to read the codebase — they open the board. Everyone's looking at the same truth.

But here's where it gets interesting.

With TodoScope, everyone on your team can see what needs doing — even AI.

Your AI assistant — Sage.is, or any MCP-compatible agent — can query this board the same way a human reads it. It can inspect what's unfinished, prioritize, and share that context with other tools and other people. No special integration. No separate API to learn. The same board. The same truth.

Your AI doesn't get a different view of the project than your humans do. Everyone's on the same page."

### Speaker Notes

- "Even AI" is the turn. Deliver it simply — don't oversell.
- Don't explain MCP or agent protocols. The audience doesn't need the plumbing.
- The key idea: AI is a teammate, not a feature. It reads the same board.
- If the audience is technical, you can mention the API briefly. If not, skip it entirely.

---

## Beat 5: The Ecosystem (8:00 – 9:30)

### Script

"TodoScope is open source. AGPL-3.0. Not open-core, not freemium — the whole thing. You can clone it right now, run it, and scan your first repo in under five minutes. Homebrew formula dropping this week — so it gets even easier.

But TodoScope is one part of something bigger.

**Sage.is AI UI** — that's the AI assistant platform that treats agents as teammates in your workflow. TodoScope is how those agents see what needs doing.

**Sage.education** — because if we're going to build tools that make collaboration accessible, we should make learning accessible too.

And **sage.is/community** — that's where all of this comes together. Developers, educators, founders, people who believe that the best tools are the ones that get out of your way and let you do the work.

"We built TodoScope because we needed it. Turns out, a lot of people do."

### Speaker Notes

- Keep the ecosystem section warm, not salesy. You're opening doors, not closing deals.
- The Sage.is AI UI mention should feel like a natural extension, not a pivot.
- Sage.education gets one line — "Plante the seed, Izzy" - don't explain the whole program.
- The community invitation is the real close. End on belonging, not product.
- "We built it because we needed it" callbacks to the founding story — this lands because it's true.

---

## Close (9:30 – 10:00)

### Script

"Collaboration can be complicated. But when everyone on your team — human and AI — can see the same truth, it gets a lot simpler.

TodoScope. No extra work.

Thank you."

### Speaker Notes

- Callback to the opening line. The audience feels the arc complete.
- "No extra work" is the last thing they hear. That's the line they'll repeat.
- Don't add a Q&A prompt here. Let the silence land. If there's a Q&A, the moderator will open it.

---

## Timing Summary

| Section | Duration | Cumulative |
|---------|----------|------------|
| Opening line | 0:05 | 0:05 |
| Beat 1: The Problem | 0:25 | 0:30 |
| Beat 2: The Insight | 0:15 | 0:45 |
| Beat 3: The Product | 6:15 | 7:00 |
| Beat 4: The Expansion | 1:00 | 8:00 |
| Beat 5: The Ecosystem | 1:30 | 9:30 |
| Close | 0:30 | 10:00 |
