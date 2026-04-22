---
name: todo-scope
description: Bootstrap and align a repo's TODO.md to TodoScope conventions. Creates TODO.md if missing, restructures messy ones, sets up .todoscope-exclude.csv, and adds cleanup TODOs for remaining work. Use when setting up a TODO.md, restructuring a roadmap, aligning a repo with TodoScope conventions, or running "todo-scope" on a project.
argument-hint: (no arguments)
---

# TodoScope — TODO.md Bootstrap & Alignment

Bootstrap and align a repo's `TODO.md` to
[TodoScope](https://github.com/Startr/TodoScope) conventions. This is housekeeping, not deep scanning. TodoScope (the application at `/Users/somma/bin/repo_scanner`) handles scanning. This gets a repo's `TODO.md` into shape so the scanner can read it.

## What This Does

One behavior, no modes. When invoked:

1. **Check for `.todoscope-exclude.csv`** — if missing, ask the user what paths to exclude and create it.
2. **Read the existing `TODO.md`** — if it exists, assess how far it has drifted from the convention. If it doesn't exist, create one.
3. **Restructure `TODO.md`** to conform — preserve existing content, reshape sections, ensure every actionable item has a checkbox, fix nesting.
4. **Add TODO items for remaining cleanup** — inline tag migration, exclude path review, whatever the repo still needs to be fully TodoScope-compatible.
5. **Offer to help** with those cleanup tasks.
6. **Encourage a convention sync check.** After everything is done, suggest the user scan the repo with their TodoScope instance and verify the board looks right. If columns or mappings don't match what they expect, offer to update this file to match.

## The Convention

The authoritative convention lives in TodoScope's `kanban.py`. We must mirror it, not the other way around — the scanner is the source of truth. The convention is:

### Inline Tags → Columns

Three tags. That's it.

| Inline tag | Kanban column  |
|------------|----------------|
| `TODO:`    | TODO           |
| `FIXME:`   | In Progress    |
| `BUG:`     | Bugs           |

`NOTE:` is informational — documentation, not a work item. Not tracked.
`DEPRECATED:` tags should be tracked as TODO items for removal at the
stated version.

Backlog has no inline tag — items land there by being placed under a
`## Backlog` section header, not by annotation.

### Section Headers → Columns

`TODO.md` section headers map to columns via case-insensitive substring
matching. Multiple aliases are supported:

| Column      | Accepted headers                                |
|-------------|-------------------------------------------------|
| In Progress | `In Progress`, `Doing`, `WIP`, `High Priority`  |
| TODO        | `TODO`, `Medium Priority`, `Tech Debt`           |
| Backlog     | `Backlog`, `Low Priority`                        |
| Bugs        | `Bugs`, `Bug`                                    |
| Done        | `Done`, `Completed`                              |

Projects can use whichever alias fits their context. `High Priority` and
`In Progress` are interchangeable. The scanner handles the mapping.

### Hashtags

Two functional tags affect board behavior:

- `#critical` — elevates a card to the top of its column
- `#bug` — overrides column placement to Bugs

All other hashtags (`#brand`, `#api`, `#ux`, etc.) are metadata — displayed
on the kanban card as inline code badges but not acted on. Tags are never
stripped; they travel with the card from TODO.md to the board. Use them
freely to describe the kind of work.

### Card Generation — The Ontology That Matters

This is the structure that produces kanban cards. Everything else is
cosmetic. Get this right and the board works.

```markdown
## Section Header              ← determines the kanban COLUMN
- [ ] **Card Title**: Desc     ← becomes a CARD on the board
  - [ ] Subtask one            ← becomes a CHECKLIST ITEM on the card
  - [x] Subtask done           ← checked item on the checklist
```

One `## header` → one column. One `- [ ] parent` → one card. Indented
`- [ ] children` → the checklist rendered on that card. That's the full
ontology.

Example — this markdown:

```markdown
## In Progress

- [ ] **Docker Image Slimming**: (Team Lead)
  - [x] Hit the ~2.5GB target (down from 9.7GB)
  - [ ] Hit the ~1.5GB base-image target after trimming heavy deps
```

generates one column ("In Progress") with one card ("Docker Image Slimming") showing a two-item checklist, one checked.

**Parent items** (the cards) need:

- A checkbox: `- [ ]` or `- [x]`
- A clear title, optionally bold: `- [ ] **Title**: Description`
- Optional category tag in brackets: `[EXTERNAL]`, `[SITE]`, `[MIXED]`
- Optional stakeholder: `(Stakeholder: Name)` or `(Name)`
- Optional hashtags: `#critical`, `#api`, `#ux`

**Subtasks** (the checklist) are indented under their parent with their
own checkboxes. Completion status is glanceable on the board without
opening the file. Keep nesting shallow — two levels is typical, three
is the practical maximum.

**Checked items** (`- [x]`) always land in the Done column, regardless
of which section they sit in. Normalize `[X]` to lowercase `[x]`.

### Organizational Extras (Nice-to-Have, Not Card-Generating)

These improve readability in the markdown file but do not affect card
generation:

**Subsection headers** (`###`) group related cards visually within a
column. The scanner does not map these to columns. Use them for topic
areas, version milestones, or categories:
`### v2.x — Near Term`, `### From Codebase (untracked)`,
`### [CSS] Framework Improvements`.

**Prose and context** (paragraphs, blockquotes, explanatory text between
items) is shown in the TodoScope interface but does not become a card.
Leave it in place — it's documentation, not a work item.

**Attribution** for items surfaced by reviews or external input:
`*(Surfaced by Name in context, YYYY-MM-DD.)*`

**Inline cross-references** link a TODO.md item to its source location:
`<!-- inline: file.py:123 -->` on the line below the subtask. Multiple
locations separated by spaces: `<!-- inline: audio.py:598,652 ollama.py:1699 -->`.

**"From Codebase (untracked)"** is a subsection under `## TODO` for
inline tags found by the scanner that don't yet have a corresponding
TODO.md entry. Group them by area (Backend, Frontend, etc.) with a
parent card summarizing the batch and subtasks listing individual
locations.

### Multiple TODO.md Files

The scanner finds TODO.md files in subdirectories too. Each card tracks
which file it came from (`TODO.md`, `docs/TODO.md`, etc.) and its line
number. When restructuring, respect the existing file locations — don't
consolidate subdirectory TODO.md files into the root unless asked.

### Kanban Column Mapping

It's important to get the column mapping right. Backlog items are often less urgent, TODO is the main queue, In Progress signals active work, Bugs need special attention, and Done tracks completed work. The scanner relies on this structure to place cards correctly. If the mapping is off, the board won't reflect reality.

## `.todoscope-exclude.csv`

CSV format with `path,reason` columns:

```csv
path,reason
node_modules,dependency cache
build,generated files
dist,generated files
__pycache__,Python bytecode cache
.venv,virtual environment
vendor,third-party dependencies
```

If the file doesn't exist, ask the user what to exclude. Common candidates:
dependency caches, build output, virtual environments, vendored code.

## Convention Header

Every TODO.md that follows the convention should include this header block
(or similar) so contributors understand the column mapping at a glance:

```markdown
> **Convention** — Sections below map to kanban columns. Inline source-code
> tags use the same vocabulary so items stay cross-referenced between this
> file and the codebase. `KANBAN.canvas` auto-generates from this file and
> inline tags — do not hand-edit it.
>
> | Column      | Markdown section  | Inline tag  |
> |-------------|-------------------|-------------|
> | Backlog     | `## Backlog`      |             |
> | TODO        | `## TODO`         | `# TODO:`   |
> | In Progress | `## In Progress`  | `# FIXME:`  |
> | Bugs        | `## Bugs`         | `# BUG:`    |
> | Done        | `- [x]` items / `## Done` | —   |
>
> `# DEPRECATED:` tags should be tracked as TODO items for removal at the
> stated version.
```

## Reference Examples

Two anonymized examples based on real projects. Study the hierarchy — section
headers set the column, subsection headers group, parent items become cards,
subtasks nest under them.

### Small project (nonprofit site)

```markdown
# TODO - Project Development Tasks

## High Priority

- **Questions for Board/Stakeholders:**
  - [ ] Verify fundraising goal amount
  - [ ] Request photos/bios for team profiles
  - [ ] Get confirmed list of volunteers
- [ ] [EXTERNAL] Business Registration Verification (Stakeholder: J.D.) #critical
  - [ ] Add English trade name in provincial registry
  - [ ] Initiate registration with provincial authority
  - [ ] Update donation platform and social media profiles
- [ ] Annual Fundraising Event — Thank-You Presentation
  - [ ] [EXTERNAL] Content & Media To Confirm (Stakeholder: V.K. / J.D.)
  - [ ] Obtain video testimony — confirm availability, length, quality
  - [ ] Collect confirmed impact numbers from recent program
- [ ] [MIXED] Event Logistics & Materials (Stakeholder: V.K.)
  - [ ] Prepare sponsorship one-pagers or table cards
  - [ ] Test A/V setup for preview playback

## Medium Priority

- [ ] [EXTERNAL] Donation Portal Configuration (Stakeholder: J.D.)
  - [ ] Upload logo files (PNG, SVG, JPG formats)
  - [ ] Create donation designations
  - [x] Test donation flow (small test transaction)
  - [ ] Configure recurring donation option

- [ ] [SITE] Translation Corrections (M.L.)
  - [ ] Audit all translated pages
  - [ ] Correct organization name across languages
  - [ ] Review key term translations

## Backlog

### [CSS] Framework Improvements
- [ ] **Host CSS Locally**: Eliminate external dependency
  - [ ] Download and save CSS as local file
  - [ ] Update templates to link local file
  - [ ] Test site functionality and commit

## Completed

- [x] [SITE] Legal Footer Implementation (M.L.)
    - [x] Verify registration number with public registry
    - [x] Add footer to all pages
    - [x] Test visibility and commit
```

### Larger project (application with backend and frontend)

```markdown
# Roadmap

This file tracks active work only.

> **Convention** — Sections map to kanban columns...
> (convention header as above)

## In Progress

- [ ] **Docker Image Slimming**: Reduce image size (Team Lead)
  - [x] Hit the ~2.5GB target (down from 9.7GB)
  - [ ] Hit the ~1.5GB base-image target after trimming heavy deps

## TODO

### v2.x — Near Term

- [ ] **Auth & Onboarding**: Email notifications and LDAP consolidation
  - [ ] Outgoing email notifications (reuse bridge SMTP config)
  - [ ] Consolidate LDAP config into Auth/Integrations tab

- [ ] **Frontend Toolchain Upgrade**: Framework and bundler updates
  - [ ] Framework v4 → v5
  - [ ] Bundler v5 → v6
  - [ ] Meta-framework to latest

- [ ] **Codebase Cleanup**: Namespace renames, semantic HTML, branding
  - [ ] DB migration (Alembic rename of tables, columns, enum values)
  - [ ] Rename `components/legacy/` directory → `components/current/`
  - [ ] Scrub remaining upstream references in comments and defaults

### v3.0 — Future

- [ ] **Backend Rewrite Research**: Evaluate framework options
  - [ ] Review research doc with team
  - [ ] Generate contract test suite from OpenAPI spec
  - [ ] Phase 0 spike: chosen framework + streaming proxy

### From Codebase (untracked)

- [ ] **Backend Inline TODOs**: Load balancing, type updates, deprecation removal
  - [ ] Intelligent load balancing for multiple backends (`api.py:1`)
  - [ ] Add retries to audio processing requests (`audio.py:1120`)
  - [ ] Remove deprecated env var fallback at next major version (`env.py:393`)

- [ ] **Frontend Inline TODOs**: UX polish, component upgrades
  - [ ] Filter order handling in model config (`Selector.svelte:34`)
  - [ ] Emoji picker search filtering (`EmojiPicker.svelte:47`)
  - [ ] Update rich text editor components to v3 (`Editor.svelte:79`)

## Backlog

- [ ] **CI/CD Pipeline**: Gated releases, scanning, regression tests
  - [ ] `make scan_container` — image scanning (post-build)
  - [ ] `make lint` — linter rollup
  - [ ] Staging instance for pre-prod testing
    <!-- inline: Makefile:572 -->
  - [ ] Browser regression tests
  - [ ] DAST scanning via `make scan_dast`

## Bugs

_No known bugs. Use `# BUG:` inline tags to flag defects in source._

## Done

> Completed items are moved to `docs/completed-todos.md` periodically.

- [x] TodoScope Alignment
  - [x] Restructure TODO.md to conventions
  - [x] Fix duplicate rows in `.todoscope-exclude.csv`
  - [x] Run scanner and verify kanban board matches expectations
```

### What to notice

- **Convention header** at the top explains the column mapping for contributors.
- **Section headers** set the column. Both files use aliases (`High Priority`,
  `Completed`, `In Progress`) that the scanner maps automatically.
- **Subsection headers** (`###`) group without affecting column placement.
  Version milestones (`### v2.x`), topic areas (`### From Codebase`).
- **Parent items** are the cards. Each has a checkbox and a clear title.
- **Subtasks** nest under parents. Two levels is typical.
- **Inline cross-references** (`<!-- inline: file:line -->`) link items
  to source locations.
- **"From Codebase (untracked)"** groups inline TODOs found by the scanner
  that haven't been manually curated yet.
- **Prose blocks** stay in place — visible in the interface, not cards.
- **Category tags** (`[EXTERNAL]`, `[SITE]`) and **stakeholder assignments**
  live on the parent line.
- **Completed items** use `- [x]` and sit in a `Done`/`Completed` section.
- **Archive reference** points to where completed items get bulk-moved.

## Rules for Restructuring

- **Preserve existing content.** Don't delete items. Reshape sections, fix
  formatting, add missing checkboxes. Move checked items to Done/Completed.
- **Preserve existing grouping.** If the TODO.md uses version milestones,
  topic areas, or subsection headers, keep them.
- **Fix nesting.** Items that are subtasks of a larger effort should be nested
  under the parent, not listed as independent top-level items.
- **Add checkboxes.** Every actionable item needs `- [ ]` or `- [x]`.
  Markdown list items and todo items become kanban cards. Other content
  (prose, headers, blockquotes) is shown in the TodoScope interface but
  doesn't land on the board.
- **Clean up empties.** Remove blank checkboxes, trailing whitespace, orphaned
  list markers.
- **Don't duplicate.** If an item already exists, don't add it again.
- **Add cleanup TODOs.** After restructuring, add items for remaining work
  the repo needs to be fully TodoScope-compatible:
  - Migrate inline tags to `TODO:` / `FIXME:` / `BUG:` conventions
  - Review `.todoscope-exclude.csv` paths
  - Any other alignment work discovered during assessment
- **Keep it concise.** Short sentences. No empty modifiers.

## What This Does NOT Do

- **No scanning.** Do not search source files for inline tags.
  TodoScope the application does that.
- **No regex.** Do not perform comment-syntax pattern matching.
- **No cross-referencing.** Do not perform fuzzy matching between inline tags and TODO.md
  items.
- **No KANBAN.canvas editing.** That file auto-generates from TodoScope. Never
  hand-edit it.
- **No `.todoscope-snapshot.json` or `.todoscope-done.json` editing.** These
  are scanner-managed files for tracking inline TODO completion over time.
