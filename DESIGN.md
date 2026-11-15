---
name: Humanitaria
description: Ask the humanitarian record. Get answers you can cite.
colors:
  field-green: "oklch(0.46 0.12 152)"
  action-green: "oklch(0.52 0.11 152)"
  citation-mist: "oklch(0.93 0.03 152)"
  on-green: "#ffffff"
  archive-paper: "#faf9f6"
  clean-sheet: "#ffffff"
  reading-room: "#f4f3f1"
  shelf-gray: "#efeeeb"
  shelf-gray-deep: "#e9e8e5"
  archive-ink: "#1a1c1a"
  graphite: "#5f5e5e"
  margin-gray: "#6b7470"
  paper-edge: "#e3e2e0"
  charcoal: "#2b2d2d"
  alert-red: "#ba1a1a"
  alert-blush: "#ffdad6"
  confirm-green: "#2e7d32"
typography:
  display:
    fontFamily: "'DM Sans Variable', system-ui, -apple-system, sans-serif"
    fontSize: "clamp(38px, 4.4vw, 56px)"
    fontWeight: 700
    lineHeight: 1.04
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "'DM Sans Variable', system-ui, -apple-system, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "'DM Sans Variable', system-ui, -apple-system, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 600
    letterSpacing: "0.05em"
  body:
    fontFamily: "'Inter', system-ui, -apple-system, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "'IBM Plex Mono', ui-monospace, 'Cascadia Code', Menlo, monospace"
    fontSize: "10px"
    fontWeight: 400
    letterSpacing: "0.14em"
  citation:
    fontFamily: "'IBM Plex Mono', ui-monospace, 'Cascadia Code', Menlo, monospace"
    fontSize: "10.5px"
    fontWeight: 600
rounded:
  sm: "2px"
  md: "6px"
  lg: "8px"
  xl: "12px"
  bubble: "16px"
  full: "9999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "24px"
  "6": "32px"
  "8": "48px"
  "10": "64px"
  "12": "80px"
components:
  button-primary:
    backgroundColor: "{colors.action-green}"
    textColor: "{colors.on-green}"
    typography: "{typography.body}"
    rounded: "{rounded.lg}"
    padding: "12px"
  button-primary-hover:
    backgroundColor: "{colors.field-green}"
  button-secondary:
    backgroundColor: "{colors.clean-sheet}"
    textColor: "{colors.archive-ink}"
    rounded: "{rounded.lg}"
    padding: "8px 14px"
  button-send:
    backgroundColor: "{colors.action-green}"
    textColor: "{colors.on-green}"
    rounded: "10px"
    size: "36px"
  input-field:
    backgroundColor: "{colors.clean-sheet}"
    textColor: "{colors.archive-ink}"
    rounded: "{rounded.md}"
    padding: "8px 10px"
  input-composer:
    backgroundColor: "{colors.clean-sheet}"
    textColor: "{colors.archive-ink}"
    rounded: "{rounded.bubble}"
    padding: "6px 6px 6px 16px"
  citation-chip:
    backgroundColor: "transparent"
    textColor: "{colors.graphite}"
    typography: "{typography.citation}"
    rounded: "5px"
    height: "18px"
  citation-chip-hover:
    backgroundColor: "{colors.field-green}"
    textColor: "{colors.on-green}"
  message-user:
    backgroundColor: "{colors.shelf-gray}"
    textColor: "{colors.archive-ink}"
    rounded: "{rounded.bubble}"
    padding: "12px 16px"
  message-assistant:
    backgroundColor: "{colors.clean-sheet}"
    textColor: "{colors.archive-ink}"
    rounded: "{rounded.bubble}"
    padding: "12px 16px"
  nav-item:
    backgroundColor: "{colors.reading-room}"
    textColor: "{colors.archive-ink}"
    rounded: "{rounded.md}"
  nav-item-active:
    backgroundColor: "{colors.shelf-gray-deep}"
    textColor: "{colors.field-green}"
---

# Design System: Humanitaria

## Overview

**Creative North Star: "The Quiet Archive"**

Humanitaria should feel like a reading room in a well-kept archive: calm, unhurried, and entirely about the material on the desk. The interface recedes so that the answer, and the report it came from, can be read without competition. Surfaces are warm paper and clean white separated by hairline edges; one green, used sparingly, marks what can be acted on or followed back to a source.

Density is moderate and generous with space. M&E staff spend long sessions here writing reports, so nothing flashes, pulses, or asks for attention it has not earned. Sources stay quiet at rest (a single line saying how many there are and who published them) and open into an orderly ledger (number, source, date) when the reader asks for them. The archive is quiet, not hidden: every citation is one click from its report.

The system explicitly rejects four looks: a generic AI chat clone, donation-campaign aesthetics, a dense enterprise dashboard, and news-site clutter.

**Key Characteristics:**
- Warm paper ground, white reading surfaces, hairline borders.
- One accent hue (green, hue 152) for actions, links, and citations; never decoration.
- DM Sans for names and headings, Inter for reading, IBM Plex Mono for labels, dates, and citation numbers.
- Flat at rest; shadow only on things that float above the page.
- Sources quiet at rest, ledger-like when opened.
- Full light and dark themes from the same token names.

## Colors

A warm-neutral paper palette with a single green voice.

### Primary
- **Field Green** (`field-green`): headings accents, links, citation text, active navigation, and the focus ring. In dark theme it brightens to a light green so text and links stay readable.
- **Action Green** (`action-green`): fills primary buttons (New chat, Send, Generate report). Hover moves it to Field Green.
- **Citation Mist** (`citation-mist`): background of citation chips and the brief flash on a source when its `[n]` is activated.

### Neutral
- **Archive Paper** (`archive-paper`): page ground.
- **Clean Sheet** (`clean-sheet`): reading surfaces: assistant messages, inputs, cards.
- **Reading Room** (`reading-room`): sidebar ground and low-emphasis panels.
- **Shelf Gray / Shelf Gray Deep** (`shelf-gray`, `shelf-gray-deep`): the user's message bubble; hover and active fills for list rows; skeleton shimmer.
- **Archive Ink** (`archive-ink`): primary text.
- **Graphite** (`graphite`): secondary text.
- **Margin Gray** (`margin-gray`): muted text, placeholders, metadata, and input outlines in light theme. A green-leaning neutral like the rest of the family (dark theme uses its own neutral green-gray), at 4.58:1 on Archive Paper so metadata stays readable. It replaced a red-brown Clay Gray (`#8e706b`) that fell below 4.5:1.
- **Paper Edge** (`paper-edge`): borders and dividers.
- **Charcoal** (`charcoal`): the Stop button while a reply streams.

### Semantic
- **Alert Red / Alert Blush** (`alert-red`, `alert-blush`): error text and error banner ground.
- **Confirm Green** (`confirm-green`): success state only; it never doubles as the accent.

Dark theme redefines every color token under `:root[data-theme='dark']` in `frontend/src/style.css` (green-tinted neutrals, hue 165–168). Components use token names only, so both themes stay in step. The marketing landing page scopes a few overrides under `.mkt-scope` in `frontend/src/marketing/marketing.css` (slightly deeper ink, `border-strong`, narrower 1160px container) with the same names.

### Named Rules
**The One Voice Rule.** Green is the only accent. It appears on things that can be acted on or followed to a source, and nowhere else. A second accent hue is not added; semantic red and green stay separate from it.

**The Paper Before Ink Rule.** Grounds are warm paper and white; depth comes from surface tone and hairline borders, not from color blocks.

## Typography

**Display Font:** DM Sans Variable (with system-ui, -apple-system, sans-serif)
**Body Font:** Inter (with system-ui, -apple-system, sans-serif)
**Label/Mono Font:** IBM Plex Mono (with ui-monospace, Cascadia Code, Menlo, monospace)

**Character:** DM Sans gives names and headings a compact, slightly geometric confidence; Inter carries long reading without fatigue; Plex Mono turns dates, counts, and citation numbers into catalog marks. All three are self-hosted through `@fontsource`.

### Hierarchy
- **Display** (700, clamp(38px, 4.4vw, 56px), 1.04): landing-page hero only.
- **Headline** (700, 1.125rem, 1.15, −0.02em): app brand title and page titles.
- **Document title** (700, 1.5rem, 1.15, −0.02em): a report's title (its country), one step above the report's own 1.25rem section heads, with type · sector · period beneath in mono 12px.
- **Title** (600, 0.75rem, uppercase, 0.05em): small section headers such as the sources header.
- **Body** (400, 1rem, 1.6): messages and reports. Assistant answers cap at 70ch.
- **Label** (mono 400, 10–11px, uppercase, 0.14–0.18em): the brand subtitle, eyebrows, the composer hint.
- **Citation** (mono 600, 10.5px): `[n]` chips and source numbers.

The type scale tokens are `--text-xs` 0.75rem, `--text-sm` 0.875rem, `--text-base` 1rem, `--text-lg` 1.125rem, `--text-xl` 1.25rem, `--text-2xl` 1.5rem, `--text-3xl` 2.5rem.

### Named Rules
**The Catalog Mark Rule.** Numbers that index or date something (citation numbers, source dates, counts) are set in IBM Plex Mono with tabular figures. Running prose never is.

## Layout

The app is a fixed-viewport shell: shared top bar above, sidebar (new chat, search, conversations) on the left, the conversation in the center, the composer pinned to the bottom. The chat view locks to the viewport; the marketing page scrolls the document. Content max width is 1280px in the app and 1160px on the landing page.

Spacing follows an 8px base grid (`--space-1` 4px through `--space-12` 80px). Messages are separated by 12px; message rows take at most 80% width (92% under 640px).

Breakpoints are written as needed, not as a fixed scale: 640px is the main one (sidebar becomes a drawer, bubbles widen, radii tighten), with 480px, 560px, 760px, and 900px used on the landing page.

**The Reading Measure Rule.** Answer and report text never runs wider than 70ch, whatever the window width. In the report viewer the whole column (header, text, Sources) shares one 70ch measure set at body size, so smaller-type blocks never shrink or drift.

## Elevation & Depth

Flat by default. Depth comes from surface tone (paper, white, reading room) and 1px hairline borders. Shadows are low-opacity and wide (`--shadow-sm` 0 1px 3px / 4%, `--shadow-md` 0 4px 12px / 4%, `--shadow-lg` 0 8px 24px / 6%) and are used only for things that sit above the page: the user menu popover, the mobile sidebar drawer and the undo toast (`lg`), and a few settings and admin panels (`sm`). The auth card carries one deeper, softer shadow of its own.

### Named Rules
**The Flat-By-Default Rule.** A surface at rest has no shadow. Shadow means "this floats above the page", not "this is important".

## Shapes

Softly curved, never pill-shaped except for avatars and toggles. Small controls use 6px (`md`), buttons and search fields 8px (`lg`), larger panels and the landing page's large buttons 12px (`xl`). Message bubbles are 16px with one tight 4px corner pointing at the speaker (top-right for the user, top-left for the assistant). Borders are 1px. The source item uses a 2px left rule as its only accent edge.

## Components

### Buttons
Refined and restrained: a solid green primary, quiet secondaries, no shadow.
- **Shape:** gently curved (8px; the send button 10px, landing large buttons 12px).
- **Primary:** Action Green fill, white text, 600 weight. Hover shifts to Field Green; the landing and send buttons also lift 1px.
- **Secondary / ghost:** white or transparent ground, Paper Edge border; hover turns border and text Field Green.
- **Press:** icon and small buttons scale to 0.94 while pressed.
- **Focus:** 2px Field Green outline, 2px offset, on `:focus-visible` only.
- **Stop:** Charcoal fill while a reply streams.

### Inputs / Fields
- **Style:** white ground, 1px Margin Gray outline, 6px radius, 8px 10px padding.
- **Focus:** border turns Field Green plus a 3px green ring at 30% (`--focus-ring`).
- **Composer:** the chat input is a 16px-radius white bar with the send button inside; on focus the whole bar takes the green border and a 16% ring. Placeholder is italic Margin Gray.

### Messages
- **User:** quiet Shelf Gray bubble with Archive Ink text, right-aligned, so the question never outweighs the answer.
- **Assistant:** white bubble with a Paper Edge border, left-aligned, answer text capped at 70ch.
- **Waiting:** before the first token arrives, two shimmering skeleton lines (the shared `.skeleton` utility) stand in for the answer; no bouncing dots.
- **Quotes:** quoted report text sits on a Reading Room fill with a 6px radius and Graphite text.
- **Error:** Alert Blush ground, a 1px border tinted from Alert Red, 6px radius, and the alert icon. The message says what happened (a connection failure names the free-tier wake-up, about 30 s), and on the last turn an outlined "Try again" resends the question in place.
- **Empty chat:** no logo tile or card grid. A left-aligned 560px column: the promise as a 1.5rem title ("Ask the humanitarian record."), one Graphite line saying answers cite their reports, a mono Label line with coverage and freshness, then example questions as hairline-ruled rows (no lift on hover), and a quiet link to M&E reports.

### Citation Chip (signature)
Every claim's `[n]` reference, quiet at rest so the answer reads first.
- **Rest:** 18px mono chip with tabular figures, transparent ground, Graphite number, 1px Paper Edge outline, 5px radius. Graphite rather than Margin Gray keeps the number quieter than body text yet well above 4.5:1.
- **Hover / focus:** Field Green fill and border with the number in On Green, so the link to the source is always one gesture away.
- **Activate:** reveals and marks its source (see Sources).
- **Name:** each chip's accessible name is the source itself ("Source 2: Title, Publisher, 2026-10-21"), not the bare number.
- **Preview:** on hover or keyboard focus a small Clean Sheet card (`--shadow-md`, 6px radius, 300px) shows the title in 13px 600 and "publisher · date" in mono, above the chip (below near the window top). The pointer can move onto it; it follows the chip on scroll; Escape closes it (`CitePreview.vue`).
- **Landing sample:** the landing page's sample answer (`SampleAnswer.vue`) uses the same chip and the same Sources ledger, so the page shows the product as it is.

### Sources (signature)
Quiet at rest, a ledger when opened (`SourceList.vue`, a native `<details>`).
- **At rest:** one line under the answer above a hairline divider: "N sources · publishers · Show" in Graphite at 0.75rem, with up to three publishers and "+N" for the rest. Show is Field Green, 600 weight.
- **Opened:** a ledger table on a white surface with a hairline border and 6px radius: columns # · Source · Date. Row numbers use the quiet citation chip; the title is a Field Green link with an external-link icon; publisher and country sit under it in Graphite; dates are ISO (YYYY-MM-DD) in mono with tabular figures. Header labels are mono uppercase, rows divided by hairlines. The toggle reads Hide.
- **From a citation:** activating `[n]` opens the ledger, scrolls to the row, flashes it in Citation Mist, moves focus to the row's link, and turns that row's number green until another citation is activated. That row shows a Field Green "Back to text" that returns to (and focuses) the chip the reader came from.
- **Focus:** the summary line takes the standard 2px Field Green focus outline.
- **Leaving the app:** copying an answer ("Copy answer with sources") or a report ("Copy with sources", beside Download PDF) appends a numbered Sources list: `[n] Title. Publisher, YYYY-MM-DD. URL` as text, and a linked `<ol>` as HTML, so pasted `[n]` markers still resolve (`utils/citationCopy.js`).

### Undo Toast
Deleting a conversation or saved report is never instant (`UndoToast.vue`, `useUndoableDelete`).
- **Behavior:** the item leaves the list at once; the DELETE is sent only after an 8 s window. "Undo" brings it back with no server call. A second delete commits the first.
- **Style:** Clean Sheet card bottom-left, 1px Paper Edge border, 6px radius, `--shadow-lg`; Field Green "Undo" text button. Keyboard focus moves to "Undo" because the deleted row has left the page.
- **Errors:** list actions that fail (open, load, delete) use the same toast in Alert Blush with an alert icon and a dismiss button, instead of failing silently.
- **Row actions:** rename and delete are revealed on hover, on keyboard focus (`:focus-within`) and always on touch screens.

### Settings & Admin
Operate surfaces in the same archive voice, never stacked cards.
- **Sections:** hairline-separated bands. Settings puts the heading in a 180px left column and the controls right (one column under 640px); Admin stacks heading, note and table over a 1120px width.
- **Labels:** one style for facts and fields: 12px, weight 600, Graphite, sentence case.
- **Data:** counts and dates in mono with tabular figures, dates as ISO (`2026-11-15`, `2026-11-15 16:31`); table headers in the ledger's mono 10px uppercase. Wide tables scroll inside their section on phones.
- **Status:** plain text with a 7px dot, Field Green and pulsing only while work runs. No status or role pills.
- **Destructive actions:** the trigger is an outlined Alert Red button; the solid red fill appears only in the confirmation dialog.

### Navigation
- **Sidebar:** Reading Room ground, 1px right border. Primary "New chat" button at the top, a search field, then the conversation list.
- **Conversation rows:** 6px radius; hover Shelf Gray, active Shelf Gray Deep with Field Green text.
- **Mobile:** under 640px the sidebar becomes a drawer with `--shadow-lg`.
- **Top bar:** one shared bar on every signed-in screen (`AppTopbar.vue`): brand title in Headline style over a mono uppercase subtitle naming the screen, linking back to chat; a Chat · Reports switch whose current item takes the active-row treatment (Shelf Gray Deep, Field Green, `aria-current="page"`); the account menu always top-right. Settings and Admin are reached from the account menu, not the switch.

## Do's and Don'ts

### Do:
- **Do** take every color from the `--color-*` tokens so light and dark themes stay in step.
- **Do** keep sources quiet at rest and one click from the report: a count line, then the ledger.
- **Do** set citation numbers, dates, and counts in IBM Plex Mono with tabular figures.
- **Do** keep answer and report text at or under 70ch.
- **Do** keep surfaces flat; use shadow only for popovers and drawers.
- **Do** honor `prefers-reduced-motion` (the global rule in `style.css` already stills animation).
- **Do** theme the browser surfaces from the palette: text selection in Citation Mist, a quiet Margin Gray scrollbar, the caret in Field Green.
- **Do** let streamed text scroll instantly; smooth scrolling is for user-triggered jumps such as a citation click.

### Don't:
- **Don't** make it look like a generic AI chat clone: no purple-blue AI gradients, glows, or anonymous gray-white chat chrome.
- **Don't** borrow donation-campaign aesthetics: no emotional hero photography, urgent orange or red, or "Help now" buttons.
- **Don't** turn screens into a dense enterprise dashboard: no wall of cards, colored KPI tiles, or badge clutter.
- **Don't** add news-site clutter: no headline walls, multi-column dense grids, or distracting imagery.
- **Don't** introduce a second accent hue or use green for decoration.
- **Don't** hide a source behind more than one interaction.
- **Don't** mark quotes, alerts, cards or list items with a thick colored side rule (over 1px); use a fill, a full hairline border, or an icon.
- **Don't** use bouncing or elastic motion, including bouncing typing dots.
- **Don't** put eyebrow or kicker labels above headings; the heading carries its own weight.
- **Don't** build a section from same-size cards of icon tile, heading and text; use headed rows or paragraphs separated by hairlines.
- **Don't** add decorative green glows, ring patterns, glass blur, or gradient fade lines.
- **Don't** hide content behind scroll-triggered fade-ins; everything is visible at rest, and the landing hero's underline on "cite." is the page's one authored motion.
- **Don't** put content in a modal when it needs neither interruption nor protected focus; the landing sample answer sits inline in the citations section.
