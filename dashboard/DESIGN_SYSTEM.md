# AgentShield dashboard — design system

The dashboard redesign (Nov 2026), made with the `frontend-design` skill (plan → review → build → critique) and the `dataviz` skill (form, colour roles, validated palette, mark specs).

## Subject, audience, job

- **Subject:** an evaluation and investigation console for AgentShield, a three-layer defence against indirect prompt injection in a local tool-using assistant.
- **Audience:**
  - security reviewers and instructors who will check every claim;
  - a live-demo audience who must follow one attack end to end.
- **Primary job:** show truthfully what happened in a run and what the recorded evidence supports. Every number traces to a log or a validated aggregate.

## Direction

An investigation console, in the family of incident-response and EDR tools. Restraint everywhere, with one memorable element: the **decision trace**.

The decision trace is the per-run ledger of proposed actions with a fixed verdict column. Each row is one proposed action and its verdict: allowed, denied by the guard, withheld by the detector, or rejected as malformed. It reads like a firewall log, which is what a security reviewer expects to audit.

## Tokens

| Role | Value | Use |
|---|---|---|
| Page | `#121418` | app background |
| Surface 1 | `#181B20` | panels, chart surface (palette validated against it) |
| Surface 2 | `#1E2228` | table headers, inputs, hover |
| Line | `#2A2F36` | hairline borders, gridlines |
| Line strong | `#363C45` | dividers, focus ring base |
| Text 1 | `#E4E7EB` | primary text |
| Text 2 | `#A9B1BC` | secondary text, axis labels |
| Text 3 | `#7C8591` | muted meta, captions |
| Accent | `#4FA3BF` | interaction only: primary button, selection, focus, links |

**Status.** These are reserved for outcomes. Every status always carries a glyph and a label: good and critical are not separable for deuteranopes (ΔE 4.7), so colour alone is never the signal.

| Status | Colour | Glyph | Meaning |
|---|---|---|---|
| Critical | `#D0605A` | ✕ | attack succeeded / task not completed |
| Good | `#4FA77A` | ✓ | blocked by Layer 3 / task completed |
| Warning | `#C99A3E` | ! | inconclusive, under review, timed out |
| Neutral | `#8A929D` | – | not attempted, benign, no result |

**Chart categorical** (configurations, only where a chart needs series identity): `#3987e5, #d95926, #199e70, #c98500, #d55181`. This is the dataviz reference dark order. On `#181B20` it passes every check (CVD worst adjacent ΔE 8.4, normal-vision 19.3, contrast ≥ 3:1). Everywhere else, identity is carried by the axis position and the bars are neutral.

## Type

- **IBM Plex Sans** for the UI and **IBM Plex Mono** only for log content: tool arguments, IDs, hashes, prompts and model text.
  - This is not a label style: no monospace small labels, no ALL-CAPS tracked eyebrows.
- **Scale:**
  - 13 px meta;
  - 14 px body and tables;
  - 16 px section headings;
  - 22 px page titles.
- **Weights:** 400 / 500 / 600. Figures in tables use tabular numerals.
- **Fallback:** if the web font cannot load (offline), the theme falls back to the system sans.

## Layout

```
┌ AgentShield ─ Overview  Simulator  Results  Evidence  Methodology ──────┐   top navigation
│ Page title                                                              │
│ one-line description of what the page answers                           │
│ ┌ panel ──────────────────────────┐ ┌ panel ─────────────────────────┐  │
│ │ dense, left-aligned content     │ │                                │  │
└─────────────────────────────────────────────────────────────────────────┘
```

- Left-aligned throughout, with a 1280 px max content width.
- **Panels:** 6 px radius, 1 px hairline, no shadows, no gradients.
- **Controls and tags:** 4 px radius.
- **Spacing steps:** 4 / 8 / 12 / 16 / 24 / 32.
- **Tables are the primary data surface;** charts appear where shape matters.

## Principles

1. **One accent, used only for interaction.** Layers are named in text, not colour-coded.
2. **Outcomes use the status set** with a glyph and a label. Attempted, succeeded, blocked by Layer 3, not attempted and inconclusive are always distinct words.
3. **Numbers carry their denominator** (for example "of 9 attempted scenarios") and are never pooled across campaigns.
4. **Numbered markers only for real sequences:** the five steps of a run.
5. **Copy names things by what users understand,** in sentence case and active voice. Errors say what happened and what to do next.
6. **No decoration:** no emoji, no glow, no gradients, no motion except Streamlit's own feedback.

## Review against the brief (generic defaults removed)

| First instinct | Why it is a default | Changed to |
|---|---|---|
| A row of big KPI tiles with coloured deltas | The SaaS-card kit | A campaign ledger table with aligned figures and their denominators |
| ALL-CAPS tracked labels on every card | The old UI did this | Sentence-case labels in text-2 |
| Meta strings `R1 · rep 1 · llama` | Middle-dot chrome | Key/value rows or table columns |
| Orange/violet/cyan per layer | Rainbow chrome | Layers named in text; the accent only for interaction |
| Q1/Q2/Q3 numbered badges | The questions are not a sequence | Plain section headings |
| Emoji icons in navigation and headers | Toy-like | Text navigation; glyphs only inside status badges |
| Monospace for small data labels | Template tell | Monospace only for log content |
