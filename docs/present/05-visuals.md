# TodoScope — Visual and Slide Recommendations

## Design Principles

1. **The product is the visual.** Prefer live demo over screenshots. Prefer screenshots over abstract graphics.
2. **Minimal text on screen.** The speaker provides the words. The visuals provide the proof.
3. **Consistent palette.** Use TodoScope's existing Kanban column colors as the presentation palette.

## Color Palette (from Kanban board)

| Element | Color | Use in Presentation |
|---------|-------|---------------------|
| Backlog header | Green | Secondary accents, positive states |
| TODO header | Gray/neutral | Body text, default states |
| In Progress header | Cyan | Highlights, active elements |
| Bugs header | Red | Warnings, problem statements |
| Done header | Purple | Ecosystem, Sage.is branding |

---

## Slide Recommendations by Beat

### Beat 1: The Problem

**Visual:** Single slide, dark background, white text.

```
"Collaboration can be complicated,
 but it doesn't have to be."
```

No logo. No graphics. Just the words. Let the speaker carry it.

**Alternative:** A progression of three grayed-out logos (Jira, Trello, Linear) with the word "stale" underneath each. Provocative but optional — only use if the audience will find it funny, not combative.

---

### Beat 2: The Insight

**Visual:** Single slide.

```
Your repo already knows
what's unfinished.
```

Below, in smaller text:

```
TODO · FIXME · BUG · NOTE · TODO.md
```

This is the only "concept" slide. Everything after is live product.

---

### Beat 3: The Product

**Visual:** Live demo — no slides.

Switch to the browser. The product is the presentation.

**Backup slides** (in case of technical failure):

1. Screenshot of the dashboard with a repo ready to scan
2. Screenshot of streaming results mid-scan
3. Screenshot of the completed Kanban board
4. Screenshot of a code.dev link opening the TODO in context

Label each backup slide clearly in the deck so you can jump to them if needed.

---

### Beat 4: The Expansion

**Visual:** The Kanban board still on screen from the demo. Overlay or transition to:

```
Everyone on your team
can see what needs doing.

Even AI.
```

Keep the board visible behind the text — the audience should see the connection between the board and the statement.

---

### Beat 5: The Ecosystem

**Visual:** Three cards or blocks, appearing one at a time:

```
┌─────────────────────────┐
│  Sage.is AI UI          │
│  AI teammates,          │
│  not features           │
└─────────────────────────┘

┌─────────────────────────┐
│  Sage.education         │
│  Accessible learning    │
│  for everyone           │
└─────────────────────────┘

┌─────────────────────────┐
│  sage.is/community      │
│  Where builders         │
│  connect                │
└─────────────────────────┘
```

Each card uses the purple/Done column color from the Kanban palette — visually linking the ecosystem to "completion" and forward motion.

---

### Close

**Visual:** Return to the opening slide format. Dark background, white text:

```
TodoScope

No extra work.
```

Below, smaller:

```
github.com/Startr/TodoScope
sage.is/community
```

---

## Screen Recording Considerations

When recording the walkthrough version:

- **Resolution:** Record at 1920x1080 minimum. The Kanban board has small text.
- **Browser chrome:** Use a clean browser profile. No bookmarks bar, no extensions visible.
- **Font size:** Increase browser zoom to 125% for readability on smaller playback screens.
- **Cursor:** Use a cursor highlighter tool so viewers can follow pointer movement.
- **Audio:** Record voiceover separately from screen capture for cleaner editing.
- **Pacing:** Pause 2-3 seconds on the Kanban board before speaking over it. Let viewers read.

## Deck Format (Self-Paced)

For the shareable deck version:

- Export slides as a PDF or use a markdown-based presentation tool (reveal.js, Marp, Slidev)
- Replace live demo sections with annotated screenshots
- Add captions below each screenshot explaining what the viewer is seeing
- Include a "Try it yourself" section at the end with installation commands
- Link to the guided tour: "Visit localhost:5000?tour=start for an interactive walkthrough"

## Assets Needed

| Asset | Status | Notes |
|-------|--------|-------|
| Demo GIF (existing) | Available | `scanner/static/Sage_repo-TODOs.gif` |
| Kanban board screenshot | Needs capture | From curated demo repo scan |
| Dashboard screenshot | Needs capture | Clean state, one repo listed |
| Streaming results screenshot | Needs capture | Mid-scan, 3-4 TODOs visible |
| Sage.is logo | Source from sage.is | For ecosystem slide |
| Speaker headshot | If needed | For conference submissions |
