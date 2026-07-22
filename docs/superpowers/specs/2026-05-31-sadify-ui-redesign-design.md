# SADify Frontend UI Redesign — Design Spec

Date: 2026-05-31
Status: Draft for review

## Traceability Sources

- `CLAUDE.md` (business-first copy; keep technical categories internal; no scope creep)
- `context.md`
- `docs/superpowers/development/01_product_scope.md`
- `docs/superpowers/development/03_data_model_and_output_schema.md`
- `apps/web/src/lib/api.ts` (the existing, unchanged backend contract)
- `apps/web/src/components/*` (the panels being recomposed)
- ui-ux-pro-max design-system output (palette, type, micro-interaction style)

## Summary

Replace the current single-page "stack of debug panels" frontend with a guided,
user-facing **AI-chat workspace**. Non-technical operations users describe a
problem in plain language, answer a short guided Q&A, and watch a System
Analysis & Design (SAD) doc build, then save it to Google Drive and update the
project wiki — all inside a calm, animated, three-pane chat app.

This is a **frontend-only redesign**. No backend route, schema, or behavior
changes. Every UI element maps to an endpoint that already exists, so the
deployment checkpoint (TC-027) is unaffected.

### Goals

- Clear, step-by-step flow a non-technical user understands without training.
- Chat-first interface with login + project/history behavior like ChatGPT/Claude.
- Adaptive 3-pane layout where pane size + color always answer "where do I look now?"
- Smooth, fluid motion; never a blank/frozen wait; legible multi-step progress.
- Friendly, bigger typography and clean Phosphor icons (no ugly line-arrows, no emoji).

### Non-Goals

- No backend changes (API, schemas, endpoints, Firestore, model prompts).
- No new product features beyond what the existing endpoints already support.
- No dark mode in this pass (tokens are theme-ready; dark is a later option).
- No change to the Q&A logic, readiness scoring, SAD synthesis, or wiki structure.

## Hard Constraint: Existing Backend, Unchanged

Every screen element is backed by a function already in `lib/api.ts`:

| UI element | Existing function / endpoint | Field(s) used |
|---|---|---|
| Sign in / session | `verifyAuthSession` `/auth/session` | id token |
| Guest "start typing" | `createGuestDraft` / `migrateGuestDraft` | guest draft id |
| Connect / status / disconnect Drive | `connectDriveRepo`, `getDriveRepoStatus`, `disconnectDriveRepo` `/drive/repo/*` | grant, status, folder |
| Attach files | `uploadSources` `/sources/upload` | `source_references`, SRC ids |
| Q&A turn | `analyzeRequirement` `/analysis/requirement` | `RequirementAnalysis` (below) |
| Answer chips | `next_question.choices` + `selection_mode` | choices, single/multiple |
| Why-this-matters | `next_question.why_this_matters` | helper text |
| Readiness ring | `readiness {label,score,confidence}` | progress |
| Coverage checklist | `categories[] {label,status}` | complete/partial/missing |
| Understanding recap | `understanding_summary` | text |
| Generate SAD | `generateSadPreview` `/sad/preview` | `SadPreviewResponse` |
| SAD doc body | `sections[] {title,body,source_references}` | sections |
| Assumptions / open questions | `assumptions[]`, `open_questions[]` | lists |
| Readiness checklist (tucked) | `it_readiness.checklist[]` | per-area status |
| Save to Drive | `saveSadPreview` `/sad/save` | `SadSaveRecord`, `sad_doc.url` |
| Update wiki | `previewWikiUpdate` / `commitWikiUpdate` `/sad/wiki/*` | files, conflicts |
| Projects list / switch / create | `listProjects`, `switchProject`, `createProject` `/projects*` | active project |
| Save history | `listProjectSaves` `/projects/{id}/saves` | per-project saves |

If a desired element has no backing function, it is out of scope.

## Design System

From the ui-ux-pro-max recommendation ("SaaS / productivity / trustworthy",
micro-interaction style). Tokens are CSS custom properties so theming stays
centralized (no raw hex in components).

```
--color-primary:    #1E3A5F   (navy — brand, sidebar, primary buttons)
--color-secondary:  #2563EB   (blue — active/emphasis, links, accents)
--color-accent:     #059669   (green — positive/CTA: New SAD, ready, success)
--color-background: #F8FAFC
--color-surface:    #FFFFFF
--color-foreground: #0F172A
--color-muted:      #F1F3F5
--color-border:     #E4E7EB
--color-warning:    #FBBF24 / #FEF9C3 bg (setup reminders, "building")
--color-destructive:#DC2626   (disconnect, sign out)
--radius: 10–16px;  --shadow: soft, low-opacity navy
```

### Typography — bigger, friendly

- Font: **Plus Jakarta Sans** (300–800), via `next/font` (no FOIT, reserved space).
- Scale (larger than current): body **16px**, secondary 14px, small label 12px;
  headings 18 / 22 / 28; weights — headings 700–800, labels 500–600, body 400–500.
- Line-height 1.5–1.6; generous whitespace; comfortable measure (60–75 chars).

### Iconography — Phosphor, soft chevron

- **Phosphor Icons** for the whole app — rounded, friendly, supports filled/duotone.
- Default size **20–24px**, consistent weight (regular/bold), one visual language.
- **Back affordance = soft chevron (`CaretLeft`)**, never an arrow-with-tail line.
- No emoji as icons anywhere. SVG only. Icons have aria-labels when icon-only.
- Implementation: **vendor the ~25 needed Phosphor SVGs as inline React
  components** in a single `Icon` module — no new dependency (decided 2026-05-31).

## App Shell & Adaptive Focus

Three panes: **Sidebar | Chat | Preview**. The active pane leads — it grows,
gains full color + a blue focus ring + slight elevation; idle panes shrink and
desaturate (strong emphasis, confirmed). A single `stage` value (derived from
app state) drives the emphasis:

| Stage | Trigger | Hero pane | Idle |
|---|---|---|---|
| `onboarding` | no analysis yet | Chat (welcome) | sidebar dim, preview placeholder |
| `clarify` | analysis in progress, <100% | **Chat** (wide, ring) | preview dim "building · NN%" |
| `review` | preview generated / 100% | **Preview** (wide, ring, green) | chat → narrow "refine" box |

Pane width transitions use spring easing (~400–450ms), never a hard snap.

## Responsive

- **Desktop ≥1024px:** all three panes; active leads.
- **Tablet 768–1023px:** Sidebar + Chat; Preview becomes a slide-in drawer
  opened by a "Preview · NN%" button (the same readiness affordance).
- **Mobile <768px:** one column; top segmented control switches **Chat ⇄ Preview**;
  a hamburger opens the Projects/account drawer. Touch targets ≥44px, safe areas
  respected, no horizontal scroll, `min-h-dvh`.

## Motion & Feedback

- Micro-interactions **150–250ms ease-out**; exits ~60–70% of enter duration.
- **Press feedback** on every clickable: scale to ~0.95 + ripple within ~100ms.
- Pane emphasis: spring `cubic-bezier(.34,1.3,.5,1)` ~450ms.
- Screen/tab/route changes: **crossfade + slight directional slide** (~250ms),
  forward slides left/up, back slides right/down.
- Animate `transform`/`opacity` only (no width/height/top/left animations → no CLS).
- **`prefers-reduced-motion`: respected** — transitions reduced to near-instant
  fades; the 1·2·3 progress and content still render, just without movement.

## Loading States — never blank, always legible

| Operation | Indicator |
|---|---|
| Q&A turn (`/analysis/requirement`) | "Assistant is thinking" — three bouncing dots in a bubble |
| Generate SAD (`/sad/preview`) | **1·2·3 phase stepper**: Reading → Drafting → Finalising |
| Update wiki (`/sad/wiki/*`) | phase stepper + "Updating N / 8 files…" count |
| Save to Drive (`/sad/save`) | **stepped**: Creating Google Doc… → Saving sources & manifest… → Saved ✓ |
| Project switch / history / sign-in | **skeleton shimmer** of the loading region |
| Any async button | disabled + inline spinner; re-enables on result |

Errors (any endpoint failure) surface as a clear inline message near the action
with a retry path, using the backend's stable error codes — plain language, no
raw stack traces.

## Screen Specs

### 1. Onboarding (merged)

- **Welcome (signed out):** centered hero in the chat pane — SADify mark,
  headline "Turn messy operations into a developer-ready spec", subtext, the
  **3 steps** (Describe → Clarify → Save), **Continue with Google** (primary),
  and a quieter **"or just start typing →"** (guest path via `createGuestDraft`).
  Sidebar + preview present but dimmed.
- **Working (after sign-in/guest):** assistant greets; user types; Q&A begins.
  Sidebar shows a live **SETUP** checklist (✓ Signed in · ○ Connect Drive "to
  save"), then Projects, then account. A soft amber **"Connect Drive to save"**
  banner sits above the composer. Drive + project requested **just-in-time at
  Save**, explained in plain language (handles `PROJECT_REQUIRED` / connect inline).

### 2. Q&A chat (chat is hero)

- Assistant question bubble with **why-this-matters** helper line.
- **Tappable answer chips** from `next_question.choices` (single or multiple per
  `selection_mode`); free-text + attach always available in the composer.
- Right pane (building, dimmed): **readiness ring** (score/label/confidence),
  **coverage checklist** with business-friendly `categories[].label` + ✓/◐/○,
  and a collapsible **"What I understand so far"** (`understanding_summary`).
- At `readiness.score` 100%: assistant posts "All required areas confirmed —
  ready to draft" with a **Generate SAD preview** button → stage `review`.

### 3. Attaching files

- **📎 in the composer bar** opens the picker. Attached files **dock as
  removable chips above the input** (filename + "N chars read · SRC-00000X"),
  with an "Add file" affordance. They are **conversation-level** (persist across
  turns via `source_references`) — never rendered as chat messages. Composer-only
  (no separate right-pane Sources list). Formats: TXT, MD, PDF, DOCX, XLSX, CSV.

### 4. SAD preview / Save / Wiki (preview is hero)

- Preview pane: title; **Draft-ready** status pill; **"Temporary — not saved
  yet"** pill (`temporary_notice`); document body from `sections[]` with
  per-section source refs; **"Assumptions we made"** (`assumptions`);
  **"Questions to confirm with the business"** (`open_questions`, business-first).
  The raw IT-readiness checklist (`it_readiness.checklist`) lives behind a
  "Review readiness checklist ▾" expander — never shown as a contradictory score.
- Action bar: **Save to Drive** (primary, navy), **Update wiki** (secondary,
  blue outline), **Refine in chat** (tertiary, ghost → returns to `clarify`).
- **Save result:** stepped progress → green "Saved to <project> · SV-00000X ·
  Open in Drive" (real Doc `sad_doc.url`); the save appears in the sidebar
  history. If no project/Drive yet, Save asks to create/connect inline first.
- **Update wiki dialog:** lists the 8 encyclopedia files with **new / updated /
  conflict** badges (`/sad/wiki/preview`); "Back up & update" commits
  (`/sad/wiki/update`); existing files are backed up before overwrite.

### 5. Sidebar — projects, history, account

- **New SAD** (green), **Drive** status row, **Projects** list (active = blue
  ring; click → `switchProject`; chat/readiness/history reload), per-project
  **save history** nested under the active project (`listProjectSaves`, each
  "Open ▸" → Doc url), **New project** (create dialog), **account** row.
- **Account / Drive menu** (from the account row): signed-in identity; Google
  Drive section (Connected · Open repo in Drive · **Disconnect Drive**); **Sign
  out**. Destructive actions are red and visually separated.

## Component Architecture

Frontend-only; recompose the existing panels into a new layout. Keep `lib/api.ts`
and all data flows (auth, `analysisSessionId`, driveRepo, projects, saves) intact.

New / reorganized components (`apps/web/src/components/`):

- `AppShell` — 3-pane responsive layout + stage-driven adaptive emphasis.
- `Sidebar` — logo, NewSAD, SetupChecklist, ProjectList, SaveHistory, AccountMenu
  (absorbs `ProjectPanel`, `ProjectHistoryPanel`, `DriveRepoPanel`, `AuthPanel`).
- `ChatThread` — message list + `ThinkingDots`; `Composer` (input + `AttachChips`)
  + `AnswerChips` (absorbs `AnalysisPanel`, `CurrentQuestion`, `SourceUploadPanel`,
  `DraftPanel`).
- `ReadinessPane` — readiness ring + `CoverageChecklist` + understanding summary
  (absorbs `ReadinessPanel`).
- `PreviewPane` — SAD doc + action bar + `SaveFlow` (absorbs `SadPreviewPanel`,
  `ChangeSummary`); `WikiDialog` (restyle `WikiUpdateDialog`); `CreateProjectDialog`
  (restyle).
- `Onboarding` / `WelcomeHero`.
- Primitives: `Icon` (Phosphor wrapper), `Button` (press/ripple/spinner states),
  `Skeleton`, `ThinkingDots`, `PhaseStepper`, `StepProgress`, `tokens.css`,
  motion utilities.

`WorkspaceShell` becomes the state container that derives `stage` and feeds the
new layout. Existing logic (session id regeneration on source/project change,
auth-restore re-fetch, idempotent save, etc.) is preserved.

## State & Stage Model

- Reuse existing React state from `WorkspaceShell` (auth user, guest draft,
  driveRepo status, active project, analysis result, preview, saves).
- Derive `stage`: no analysis → `onboarding`; analysis present & <100% →
  `clarify`; preview present → `review`. `stage` drives pane emphasis + responsive
  default pane on mobile.
- No new global state library; local state + existing fetch helpers.

## Dependencies

- **No new dependencies.** Phosphor icons are vendored as inline React SVG
  components (decided 2026-05-31) in one `Icon` module.
- Plus Jakarta Sans via `next/font/google` (no package).

## Accessibility

- Contrast ≥4.5:1 (verified pairs on light surfaces); visible focus rings;
  keyboard nav with logical order; icon-only buttons have aria-labels; answer
  chips are real buttons; toasts use `aria-live`; `prefers-reduced-motion`
  honored; touch targets ≥44px; respects system text scaling.

## Out of Scope / Risks

- Drive Picker (folder selection UI) — still future; connect creates/uses the
  default repo folder as today.
- Wiki backup remains download+upload (backend behavior unchanged).
- Risk: large recompose of 13 components — mitigated by keeping `api.ts` and data
  flows untouched and migrating panel-by-panel behind the new shell.
- No icon dependency (inline SVGs), so no third-party icon risk.

## Deployment Impact

None to the backend. The frontend container build (TC-027) is unaffected in
shape; only `apps/web` source changes. Recommended sequence: ship this redesign,
then proceed to TC-027 two-service deploy.
