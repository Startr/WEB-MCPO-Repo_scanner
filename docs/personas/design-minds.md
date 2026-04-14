# Design Minds — Research for TodoScope

Reference document for the design voices and research informing TodoScope's landing page and UI decisions.

## Foundational Thinkers

### Dieter Rams — "Less, but better"
Industrial designer whose 10 Principles for Good Design are the blueprint for Startr.style's philosophy. Core principles relevant to TodoScope:
- Good design is as little design as possible
- Good design is honest
- Good design is unobtrusive
- Good design makes a product useful

His influence runs through Apple (via Jony Ive), Braun, and the modern minimalist web. TodoScope should feel like a Rams product — nothing to remove, nothing to add.

### Don Norman — The Godfather of UX
Coined "user experience," wrote *The Design of Everyday Things*. Core principle: design should communicate how things work without requiring explanation. Critical for self-hosted tools where there's no onboarding email or support chat — the UI itself has to teach.

### Jony Ive — The Family of Products
Carried Rams' philosophy into digital at Apple. Key insight: *create a family of products that feel related, behave intuitively, and look timeless together.* TodoScope, Sage, and Startr.style should feel like siblings.

## The Developer-Designer Bridge

### Adam Wathan & Steve Schoger — Refactoring UI
The most directly applicable resource for developer-built UIs. Wathan created Tailwind CSS; Schoger is a designer. Their book teaches professional UI without a designer on staff.

Tactical advice that maps to Startr.style:
- Give elements more breathing room than feels necessary
- Use visual hierarchy (size, weight, color) instead of layout complexity
- Shadows and subtle borders create depth without clutter
- Limit your color palette — a few well-chosen shades beat a rainbow
- Start with too much whitespace, then remove

### Nicole Sullivan — OOCSS Pioneer
Her 2009-2011 work on Object-Oriented CSS directly inspired the utility-first approach that became Tailwind and, by extension, Startr.style.

## Product Design Leadership

### Julie Zhuo — Purpose, People, Process
Former VP of Product Design at Facebook (~14 years), now co-founder of Sundial (product strategy advisory). Her framework: Purpose, People, Process. For small teams: *don't design for the average user — design for the specific person you're trying to help.* That's our "solo founder, small team, underdog" lens.

## Dev Tool Landing Page Research

### Evil Martians — 100 Dev Tool Landing Pages Study (2025)
Source: https://evilmartians.com/chronicles/we-studied-100-devtool-landing-pages-here-is-what-actually-works-in-2025

The single most useful tactical resource for TodoScope's landing page. Studied Linear, Vercel, Supabase, and 97 others.

#### Two Golden Rules
1. "No salesy BS"
2. "Clever and simple wins"

Avoid flashy interactions. Prioritize clean design, solid typography, clear layouts.

#### Hero Section
- **Centered composition dominates** — bold headline + supporting visual below
- Side-by-side text/image layouts are rare and less effective in dev tools
- Visual options: product screenshots, code snippets, live embedded UI, or abstract illustrations
- Eyebrow text above title for releases/milestones is effective

#### Calls-to-Action
- Deploy **two CTAs** with different visual treatment
- Bold primary with specific language ("Start building" beats "Get started")
- Lighter secondary (docs, GitHub, waitlist) — must not compete visually
- Final page CTA: "big and loud," full-width block, distinct background, single clear objective

#### Feature Storytelling (weakest to strongest)
1. Simple function lists (least persuasive)
2. Action-oriented tasks ("Build faster," "Run anywhere")
3. Problem-oriented narratives (addressing user pain points)
4. Bold, opinionated statements (best for established products)
5. Mission-statement approaches (rare but powerful when authentic)

#### Trust Signals
- **Open-source tools**: GitHub stars, usage metrics, awards — not enterprise logos
- Manually curated testimonials > auto-pulled social content
- Even one sentence from a first user beats nothing
- Advanced: integrate quotes next to specific features, not in a separate section

#### Layout Patterns
- Chess layout (alternating left/right image-text blocks)
- Bento-style grids for visual variety
- Text with icons for SDKs and libraries
- Step-by-step workflows
- Tabbed features for logical grouping

#### Critical Mistakes
- Generic CTA language ("Get started" instead of product-specific text)
- Auto-embedded social content without moderation
- Salesy language or flashy interactions
- Cluttered layouts without breathing room
- Feature lists disconnected from user problems

## Open-Source Design Tools

### Penpot
Most production-ready open-source design tool in 2026 (self-hostable). Philosophical cousin — same ethos: open, self-hosted, no lock-in. Their 2.0 added CSS Grid Layout, rebuilt component system, and native design tokens.

## How This Applies to TodoScope

1. **Centered hero** — headline is the pitch, subline is the inversion, GIF below
2. **Two CTAs** — "Sign in" (primary) + "View on GitHub" (secondary, lighter)
3. **Problem-oriented features** — not "it scans files" but "TODOs pile up. Your AI can't see them."
4. **MCP section** — code snippet showing a real Sage/Claude query
5. **Trust signal** — GitHub stars + "self-hosted, your data never leaves this server"
6. **Breathing room** — generous spacing, shadows for depth (Startr.style `--shadow:4;`)
7. **No salesy BS** — founder voice per the brand interview
