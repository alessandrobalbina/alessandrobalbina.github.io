# Other Projects (`/other-projects/`) Visual & Copy Enhancements Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve scannability, visual hierarchy, and storytelling on `/other-projects/` and `/it/other-projects/` while preserving strict EN/IT parity and the existing design system.

**Architecture:** Pure static HTML/CSS enhancements reusing existing `.card`, `.tag-list`/`.tag`, and `.pub-btn` tokens in `styles.css`, plus a responsive 3-column bento/sub-card layout (`.passions-grid`) inside the Passions & Personal Projects section.

**Tech Stack:** Static HTML5, Vanilla CSS3 (CSS Grid/Flexbox, CSS custom properties).

## Global Constraints

- Maintain strict EN/IT bilingual parity between `other-projects/index.html` and `it/other-projects/index.html`.
- Preserve CSP (`default-src 'self'`), dark mode compatibility, and WCAG AA/AAA contrast.
- Zero external dependencies or inline scripts.

## Review Focus

- Mobile responsiveness of the 3-card `.passions-grid` (collapse cleanly to 1 column below `768px`).
- Dark mode contrast for any subtle borders/backgrounds on sub-cards.
- Consistent icon sizing (`15px–18px`) matching `.tag-icon` and `.pub-btn-icon`.
- Proper `rel="noopener noreferrer"` and `target="_blank"` on external links (`jamboree.it`, `lufrix.me`).

---

### Task 1: Upgrade Hero Lead & AGESCI Role Pills + Jamboree CTA

**Files:**
- Modify: `other-projects/index.html:183-228`
- Modify: `it/other-projects/index.html:177-208`
- Modify: `styles.css:2295-2330`

- [x] Replace the generic `.lead` copy with a sharper, personal summary connecting scouting, outdoors, and creative tech.
- [x] Add a compact `.tag-list` row below `.scout-header` highlighting key milestones (`Since 2007`, `Wood Badge · 2025`, `Group Leader · Cagliari 5`, `CMT Communication · WSJ 2027`).
- [x] Add a clean `.pub-btn` CTA (`Jamboree.it →`) inside `.jamboree-block` so the co-developed site stands out as a tangible deliverable.

---

### Task 2: Restructure "Passions & Personal Projects" into a 3-Card Grid

**Files:**
- Modify: `other-projects/index.html:230-245`
- Modify: `it/other-projects/index.html:210-222`
- Modify: `styles.css` (add `.passions-grid` & `.passion-item`)

- [x] Split the two dense paragraphs into 3 scannable sub-cards inside `.passions-grid`:
  1. **Outdoor & Photography**: Sardinia mountain trails (Pischina Urtadala, Sa Giuntura), Val Codera, Brenta Dolomites, Circeo.
  2. **Vibe Coding & Local Digital Tools**: Concept for a collaborative "natural shopping center" platform for local businesses.
  3. **3D Printing & Prototyping**: Hands-on CAD/3D printing experiments.
- [x] Add a subtle static SVG icon per sub-card and responsive mobile stacking.
