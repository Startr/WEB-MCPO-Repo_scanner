# TodoScope — In-App Guided Tour

## Concept

The TodoScope UI becomes the presentation itself. A guided tour framework overlays step-by-step prompts on the live application, walking new users through the experience while the real product runs underneath.

This replaces a traditional slide deck. The audience sees the actual product, not screenshots of it.

## Framework Options

Choose a JS guided tour library that supports:

- Step-by-step highlighting of DOM elements
- Custom tooltip positioning and styling
- Progress indicators
- Keyboard navigation (arrow keys, escape)
- Mobile-responsive overlays
- Easy integration with existing Flask templates

**Candidates to evaluate:**

| Library | Notes |
|---------|-------|
| Shepherd.js | Popular, well-maintained, Tether-based positioning |
| Intro.js | Lightweight, simple API, step-based |
| Driver.js | Modern, no dependencies, smooth animations |
| Hopscotch | LinkedIn-built, multi-page tour support |

The choice of library is secondary to the tour content. Pick whichever integrates cleanest with the existing template structure.

---

## Tour Structure

The tour maps directly to the 5-beat narrative arc.

### Tour 1: First Visit (Dashboard)

**Triggers on:** First login or manual activation via "Take a Tour" button

**Steps:**

1. **Welcome overlay** (no element highlight)
   > "Collaboration can be complicated, but it doesn't have to be. Let's show you how TodoScope works."

2. **Highlight: Repository URL input**
   > "Point TodoScope at any Git repository — paste a URL and hit Scan."

3. **Highlight: Add Local Repository**
   > "Or add a project that's already on your machine. The path never leaves your computer."

4. **Highlight: Repository table** (if repos exist)
   > "Repos you've scanned before are listed here. Click 'View TODOs' to rescan anytime."

5. **Action prompt**
   > "Try it — enter a repo URL and click 'Scan Repository' to see it in action."

---

### Tour 2: Scan Results

**Triggers on:** First time viewing scan results, or continuation from Tour 1

**Steps:**

1. **Highlight: Streaming TODO list**
   > "TodoScope scans every file and surfaces TODO, FIXME, BUG, and NOTE comments as it finds them — in real time."

2. **Highlight: A single TODO item**
   > "Each item shows you exactly where it lives — file, line number, and a direct link to edit it."

3. **Highlight: TODO.md section**
   > "If your project has a TODO.md or TODO.txt, it shows up here with full markdown rendering."

4. **Highlight: Kanban board**
   > "And here's the board. Five columns, built entirely from what's in your code. Nobody moved a card — the board built itself."

5. **Highlight: Kanban column headers**
   > "TODO comments map to columns automatically. TODO → TODO. FIXME → In Progress. BUG → Bugs. NOTE → Backlog. Checked items → Done."

6. **Highlight: Guide section toggle**
   > "Want to see exactly how items map to columns? Open this guide anytime."

7. **Highlight: Rescan button**
   > "Update your code, hit Rescan, and the board reflects reality. No extra work."

---

### Tour 3: The AI Angle

**Triggers on:** After Tour 2 completes, or as a standalone explainer

**Steps:**

1. **Highlight: No specific element — overlay**
   > "Everything you just saw? Your AI assistant sees the same thing."

2. **Highlight: Footer or Sage.is branding**
   > "Sage.is AI and any MCP-compatible agent can query TodoScope's API — same board, same data, same truth."

3. **Highlight: No element — overlay**
   > "Everyone on your team can see what needs doing. Even AI."

---

### Tour 4: The Ecosystem

**Triggers on:** After Tour 3, or via "Learn More" link

**Steps:**

1. **Overlay**
   > "TodoScope is part of something bigger."

2. **Overlay with links**
   > "**Sage.is AI UI** — AI assistants that work as teammates, not features."
   > "**Sage.education** — Making learning as accessible as the tools."
   > "**sage.is/community** — Where builders, educators, and developers connect."

3. **Final overlay**
   > "TodoScope is open source. AGPL-3.0. Built for everyone who needs to see how a project is going."

---

## Implementation Notes

### Where to add the tour code

- Add the tour library CSS/JS to [base.html](../../scanner/templates/base.html)
- Define tour steps in a dedicated JS file: `scanner/static/js/tour.js`
- Tour state (completed/skipped) stored in localStorage to avoid repeat triggers

### Tour activation

- **Automatic:** Trigger on first visit (check localStorage flag)
- **Manual:** Add a "Take a Tour" button in the header/nav area
- **Presentation mode:** URL parameter `?tour=start` forces the tour regardless of localStorage

### Styling

- Tour tooltips should match TodoScope's existing visual language
- Use the same color palette as the Kanban column headers
- Keep tooltip text short — one to two sentences per step
- Progress dots at the bottom of each tooltip

### Accessibility

- Tour must be keyboard-navigable (arrow keys, escape to dismiss)
- Tooltips should have sufficient contrast
- Screen reader support for tour content
- "Skip tour" option always visible
