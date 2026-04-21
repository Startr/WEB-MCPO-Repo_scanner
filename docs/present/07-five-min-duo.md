# TodoScope: See What's Actually Unfinished
## Five-Minute Duo Presentation, Izzy & Alex

---

### ACT 1, The Problem (Izzy, ~90 seconds)

**[Izzy walks up alone]**

You know what nobody tells you about building a startup?

The code isn't the hard part. The communication is.

I'm Izzy, I'm the cofounder of Startr and Sage.is. I'm not writing code every day. But I need to know what's happening in our codebase. What's critical. What's next. What's stuck.

And here's what that actually looks like:

I sit beside Alex, for hours, just to grasp the full context of what's being worked on. Not because he's bad at communicating. Because the information lives in his head and in the code, and there's no bridge between the two.

I can't see what's top priority at all times. So sometimes I push Alex to work on things that really should be in a backlog. Good intentions, wrong target.

And here's the thing that keeps me up at night, we have a teammate who is amazing with us. He kept asking for tasks. For weeks. And we couldn't hand them to him fast enough. Not because we didn't have work, because packaging up context was more work than just doing it ourselves.

Every team has this problem. You just stop noticing it after a while.

**[Beat]**

Alex noticed.

---

### ACT 2, The Solution (Alex, ~90-120 seconds)

**[Alex steps up, laptop open]**

So, I built the bridge.

And Izzy called it TodoScope. And I want to show you, not tell you.

**[Live demo, scan the Sage.is AI-UI repo]**

This is our actual repo for Sage.is AI-UI. Real code. Real TODOs.

**[Runs the scan]**

TodoScope scans your codebase and finds every TODO, FIXME, BUG, and NOTE your team has left in the code. The comments you're already writing. No new habits. No tickets to file. No board to maintain.

**[Kanban board appears]**

And it turns them into this. A Kanban board, generated from your code. Priorities visible. Context intact. Click any item and you're in your editor, on that line.

Izzy can see what I'm working on without sitting beside me for two to twenty hours. Our teammates can pull up the board and pick a task without waiting for me to package it up. And when I mark something as done in the code, it's done on the board.

No syncing. No stale tickets. No context switching.

The board lives where the work lives.

**[Turns to Izzy]**

Izzy, you use this?

---

### ACT 3, The Endorsement & Close (Together, ~60 seconds)

**[Izzy]**

I use this. I can see priorities without asking. I can see what's in progress without interrupting anyone. And I stopped accidentally pushing the team toward the wrong things, because now I can see what actually matters.

**[Alex]**

Our Startr/TodoScope is open source. It runs locally, it runs in Docker, it takes about two minutes to set up. It also speaks MCP, so if you're building with AI agents, they can read the same board your team reads.

**[Izzy]**

We built this because we needed it. We're sharing it because you probably need it too.

**[Alex]**

**[Shows URL on screen]**

Go to our GitHub and scan your first repo tonight. If you write TODOs, you already have a board. You just can't see it yet.

**TodoScope makes it visible.**

---

## Speaker Notes

### Izzy, Act 1
- Tone: Conversational, a little frustrated, honest. Not performing, sharing.
- The three problems should land as an escalating sequence: personal inconvenience → team blindness → losing a contributor. Each one is bigger than the last.
- The volunteer/teammate story is the emotional anchor. Don't rush it.
- "Alex noticed.", This is a handoff line. Pause after it. Let it land.

### Alex, Act 2
- Tone: Calm, confident, showing not selling. Let the tool speak.
- The demo should be prepped and tested. Have Startr.Style repo as a backup if Sage.is AI-UI takes too long to scan.
- Keep narration during the demo minimal. Let the audience watch the board build itself.
- "No syncing. No stale tickets. No context switching.", This is the thesis. Deliver it clearly.
- The turn to Izzy ("You use this?") should feel natural, not staged. It's a genuine check-in that doubles as a transition.

### Together, Act 3
- Izzy's endorsement should be brief and specific. Three concrete things that changed.
- The MCP mention is one sentence, plant the seed, don't explain it. The developers who care will find it.
- The CTA is: scan your first repo tonight. Specific. Actionable. Tonight, not "someday."
- Final line is the tagline: "TodoScope makes it visible." End clean.

### Timing Guide
| Section | Speaker | Target | Max |
|---------|---------|--------|-----|
| Act 1, Problem | Izzy | 75s | 90s |
| Act 2, Demo | Alex | 100s | 120s |
| Act 3, Close | Both | 45s | 60s |
| **Total** | | **~4 min** | **~4.5 min** |

Buffer of 30 seconds built in for demo loading, laughter, and transitions.

### Demo Checklist
- [ ] Sage.is AI-UI repo cloned and accessible
- [ ] Startr.Style repo ready as backup (smaller, faster scan)
- [ ] TodoScope running locally, tested within the hour
- [ ] Browser open, font size large enough for back of room
- [ ] WiFi tested (or run fully local to avoid dependency)
- [ ] Screen share or projector tested with Kanban view

### Stage Setup
- Izzy starts alone. Alex joins naturally, not a dramatic entrance, just stepping up.
- One laptop, one screen. Keep it simple.
- URL displayed on final slide or screen at the end. Large. Readable.

## Suggested Visuals

For a five-minute presentation with a live demo, **less is more**. Consider:

1. **No slides during Acts 1 and 2.** Izzy speaks without visual support (more intimate). Alex's demo IS the visual.
2. **One closing screen** with:
   - TodoScope logo / name
   - GitHub URL
   - One line: "Scan your first repo tonight."
3. If you want a safety net behind Izzy during Act 1, a single slide with the three problems as short lines that appear as she names them:
   - "Hours of context transfer"
   - "Invisible priorities"
   - "Contributors left waiting"

That's it. The demo does the heavy lifting. Trust it.
