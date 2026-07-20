# SADify Frontend UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace SADify's stacked debug-panel frontend with a guided 3-pane AI-chat workspace (adaptive focus, smooth motion, friendly Phosphor icons), changing only `apps/web` and the Python static UI tests — no backend changes.

**Architecture:** Recompose the existing ~13 panels into a new `AppShell` (Sidebar | Chat | Preview) whose emphasis is driven by a derived `stage`. Keep `lib/api.ts` and all data flows in `WorkspaceShell` intact; restyle with CSS Modules + a central design-token file; vendor Phosphor icons as inline SVG React components (no new dependency).

**Tech Stack:** Next.js 16 / React 19 / TypeScript, plain CSS + CSS Modules (no Tailwind), Plus Jakarta Sans via `next/font/google`. Verification: `tsc --noEmit`, `next lint`, `next build`, Python static UI tests, manual browser smoke.

---

Date: 2026-05-31
Status: Complete - shipped on branch `codex/mvp-monorepo-scaffold` (commits 05fb247..56f647d, Codex follow-up de7209f). `tsc --noEmit` clean, static UI tests green, `next build` OK. Closed 2026-06-02.

Spec: `docs/superpowers/specs/2026-05-31-sadify-ui-redesign-design.md`
Visual source of truth (locked mockups): `D:\GoogleCloudHack\.uiframes\ui\*.html`
(index.html links each screen — exact colors, spacing, layout, icons live there).

## Worktree

Work in the existing MVP worktree:
`D:\GoogleCloudHack\.worktrees\mvp-monorepo-scaffold`, branch
`codex/mvp-monorepo-scaffold`. Confirm HEAD is the latest persistence commit
(`c2166cd` or newer) and the tree is clean before starting.

## Hard Constraints (Stop Rules)

- **No backend changes.** Do not touch `services/`, `src/sadify/`, schemas, or
  `lib/api.ts` request/response shapes. UI consumes existing functions only.
- **No new runtime dependencies.** Icons are inline SVG; font via `next/font`.
- Every async action shows a loading state (Section "Loading primitives"); no
  blank/frozen waits.
- Keep all existing `WorkspaceShell` logic: `analysisSessionId` regeneration on
  source/project change, auth-restore re-fetch of `/drive/repo/status`, idempotent
  save, guest-draft migration.
- Business-first copy; technical category ids stay internal (use the human
  `label` fields the API already returns).
- Update the Python static UI tests in the SAME task that changes the structure
  they assert on. Never delete a test to make it pass — rewrite its assertions to
  the new structure with equivalent coverage.

## Verification Commands (used throughout)

```bash
# from apps/web
npx -y tsc --noEmit          # types (primary gate)
npm run lint                 # next lint
npm run build                # next build (run at phase boundaries; slow)
# from worktree root (Windows PowerShell env):
#   set PYTHONPATH=services\api\src;src;.  &&  set SADIFY_DRIVE_MODE=local
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest tests/test_mvp_*_ui.py tests/test_mvp_workspace_shell.py tests/test_mvp_scaffold.py -q
```

Manual browser smoke is drip-fed per screen by the user (run backend in local
mode + `npm run dev`), graded against the matching mockup.

## File Structure (what gets created / changed)

New (all under `apps/web/src`):

```
styles/tokens.css                 # CSS variables: colors, type scale, radius, shadow, motion
components/ui/Icon.tsx             # ~25 inline Phosphor SVG icons + <Icon name=.. size=..>
components/ui/Button.tsx (+.module.css)        # press/ripple/spinner states
components/ui/Skeleton.tsx (+.module.css)
components/ui/ThinkingDots.tsx (+.module.css)
components/ui/PhaseStepper.tsx (+.module.css)  # 1·2·3 phase indicator
components/ui/StepProgress.tsx (+.module.css)  # stepped Drive-save progress
components/shell/AppShell.tsx (+.module.css)   # 3-pane responsive + adaptive emphasis
components/shell/Sidebar.tsx (+.module.css)
components/shell/SetupChecklist.tsx
components/shell/ProjectList.tsx
components/shell/SaveHistory.tsx
components/shell/AccountMenu.tsx
components/chat/ChatThread.tsx (+.module.css)
components/chat/Composer.tsx (+.module.css)
components/chat/AttachChips.tsx
components/chat/AnswerChips.tsx
components/chat/ReadinessPane.tsx (+.module.css)
components/chat/CoverageChecklist.tsx
components/preview/PreviewPane.tsx (+.module.css)
components/preview/SaveFlow.tsx
components/preview/WikiDialog.tsx (+.module.css)
components/onboarding/WelcomeHero.tsx (+.module.css)
lib/stage.ts                      # deriveStage(state) -> 'onboarding'|'clarify'|'review'
```

Modify:

```
app/layout.tsx                    # Plus Jakarta Sans via next/font; import tokens.css
app/globals.css                   # reduce to reset + token import (light theme)
components/WorkspaceShell.tsx      # becomes state container -> renders AppShell
tests/test_mvp_*_ui.py, tests/test_mvp_workspace_shell.py   # update assertions per task
```

Remove only after their behavior is fully migrated (final task):
old presentational panels (`DraftPanel`, `DriveRepoPanel`, `SourceUploadPanel`,
`AnalysisPanel`, `CurrentQuestion`, `ReadinessPanel`, `SadPreviewPanel`,
`ProjectPanel`, `ProjectHistoryPanel`, `ChangeSummary`, `AuthPanel`) — or keep as
thin re-exports if a static test still needs the filename (decide per test).

---

## Phase 0 — Foundations (no behavior change)

### Task 1: Design tokens + font + global reset

**Files:**
- Create: `apps/web/src/styles/tokens.css`
- Modify: `apps/web/src/app/globals.css`
- Modify: `apps/web/src/app/layout.tsx`

- [ ] **Step 1: Create `tokens.css`** with the spec palette + scales:

```css
:root {
  --c-primary:#1E3A5F; --c-on-primary:#fff; --c-secondary:#2563EB;
  --c-accent:#059669; --c-bg:#F8FAFC; --c-surface:#FFFFFF; --c-fg:#0F172A;
  --c-muted:#F1F3F5; --c-border:#E4E7EB; --c-warn:#FBBF24; --c-warn-bg:#FEF9C3;
  --c-danger:#DC2626; --c-subtle:#64748B; --c-ring:#2563EB;
  --r-sm:8px; --r-md:11px; --r-lg:16px;
  --sh-1:0 4px 14px rgba(15,23,42,.08); --sh-2:0 8px 28px rgba(15,23,42,.12);
  --fs-body:16px; --fs-sec:14px; --fs-label:12px;
  --fs-h1:28px; --fs-h2:22px; --fs-h3:18px;
  --motion-fast:180ms; --motion-mid:250ms; --ease-out:cubic-bezier(.22,.61,.36,1);
  --ease-spring:cubic-bezier(.34,1.3,.5,1);
}
@media (prefers-reduced-motion: reduce){
  :root{ --motion-fast:1ms; --motion-mid:1ms; }
}
```

- [ ] **Step 2: Rewrite `globals.css`** to a light-theme reset that imports tokens (remove the dark `.workspace` styles — they belong to the old shell which we replace in Task 5+; keep file importing tokens and base element styles):

```css
@import "../styles/tokens.css";
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--c-bg);color:var(--c-fg);min-height:100dvh;
  font-size:var(--fs-body);line-height:1.55;
  font-family:var(--font-jakarta), system-ui, sans-serif;}
button,textarea,input,select{font:inherit;color:inherit}
a{color:var(--c-secondary)}
:focus-visible{outline:2px solid var(--c-ring);outline-offset:2px}
```

- [ ] **Step 3: Wire Plus Jakarta Sans in `layout.tsx`** via `next/font/google`, exposing `--font-jakarta`:

```tsx
import { Plus_Jakarta_Sans } from "next/font/google";
const jakarta = Plus_Jakarta_Sans({ subsets:["latin"], weight:["400","500","600","700","800"], variable:"--font-jakarta", display:"swap" });
// add className={jakarta.variable} to <html> (or <body>)
```

- [ ] **Step 4: Verify** `npx -y tsc --noEmit` (clean) and `npm run build` (compiles; the old shell may still reference removed `.workspace` classes — if build/types fail because WorkspaceShell uses them, that is expected and fixed in Phase 1; if you need green here, defer the globals.css class removal to Task 5 and only ADD tokens import now).
- [ ] **Step 5: Commit** `feat(ui): design tokens, Plus Jakarta Sans, light reset`.

### Task 2: Inline Phosphor icon module

**Files:** Create `apps/web/src/components/ui/Icon.tsx`

- [ ] **Step 1: Implement `Icon`** — a typed wrapper rendering inline Phosphor
  SVG paths. Include exactly the icons the mockups use: `sparkle, folder,
  cloudCheck, clock, paperclip, fileText, book, uploadCloud, user, googleG,
  caretLeft, caretRight, plus, check, circle, halfCircle, info, question, eye,
  edit, arrowRight, openExternal, signOut, x, swap`. Stroke 1.9, round caps,
  24px default. **Back = `caretLeft` (soft chevron), never an arrow with a tail.**

```tsx
type IconName = "sparkle"|"folder"|"cloudCheck"|"clock"|"paperclip"|"fileText"
 |"book"|"uploadCloud"|"user"|"googleG"|"caretLeft"|"caretRight"|"plus"|"check"
 |"circle"|"halfCircle"|"info"|"question"|"eye"|"edit"|"arrowRight"
 |"openExternal"|"signOut"|"x"|"swap";
const P: Record<IconName,string> = {
  caretLeft:"M15 6l-6 6 6 6",            // soft chevron back
  check:"M5 12l4 4L19 7",
  plus:"M12 5v14M5 12h14",
  // ...fill remaining paths from the mockups' <defs> (Phosphor style, rounded)
} as unknown as Record<IconName,string>;
export function Icon({name,size=24,color="currentColor",stroke=1.9}:{name:IconName;size?:number;color?:string;stroke?:number}){
  return (<svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round"
    aria-hidden="true"><path d={P[name]}/></svg>);
}
```

- [ ] **Step 2:** Fill every path from the mockup `<defs>` (`.uiframes/ui/*.html`),
  Phosphor-rounded. For icons that read better filled (folder active, googleG),
  add an optional `filled` variant. Each icon used by an icon-only button must be
  wrapped by a labelled `<button aria-label="…">` at call sites.
- [ ] **Step 3: Verify** `npx -y tsc --noEmit`.
- [ ] **Step 4: Commit** `feat(ui): inline phosphor icon set with soft-chevron back`.

### Task 3: Loading + interaction primitives

**Files:** Create `Button`, `Skeleton`, `ThinkingDots`, `PhaseStepper`,
`StepProgress` under `components/ui/` (+ matching `.module.css`).

- [ ] **Step 1: `Button.tsx`** — variants `primary|secondary|ghost|danger`,
  `loading?:boolean`. Press: `transform:scale(.95)` on `:active`; ripple via a
  span appended on click; when `loading`, disable + show inline spinner. Timings
  from tokens (`--motion-fast`, `--ease-out`). Reduced-motion disables ripple/scale.

```tsx
export function Button({variant="primary",loading,children,onClick,...rest}:Props){
  function handle(e:React.MouseEvent<HTMLButtonElement>){ if(loading)return;
    ripple(e); onClick?.(e); }
  return <button className={cx(styles.btn,styles[variant],loading&&styles.loading)}
    disabled={loading||rest.disabled} onClick={handle} {...rest}>
    {loading && <span className={styles.spin} aria-hidden/>}{children}</button>;
}
```

- [ ] **Step 2: `Skeleton.tsx`** — shimmer block (`width`,`height` props), CSS
  keyframe gradient sweep; honors reduced-motion (static muted block).
- [ ] **Step 3: `ThinkingDots.tsx`** — three bouncing dots in a bubble; staggered
  delays; reduced-motion → static "…".
- [ ] **Step 4: `PhaseStepper.tsx`** — props `phases:string[]`, `active:number`;
  renders numbered 1·2·3 with the active one lit + connector bars. Used for
  generate/wiki.
- [ ] **Step 5: `StepProgress.tsx`** — props `steps:{label:string;state:'pending'|'active'|'done'}[]`;
  spinner on active, check on done. Used for Drive save.
- [ ] **Step 6: Verify** `npx -y tsc --noEmit` and render each on a scratch route
  `app/_uikit/page.tsx` (temporary) to eyeball; delete the scratch route before commit.
- [ ] **Step 7: Commit** `feat(ui): button, skeleton, thinking dots, phase + step progress`.

---

## Phase 1 — App shell + stage model

### Task 4: Stage model

**Files:** Create `apps/web/src/lib/stage.ts`; Test
`tests/test_mvp_workspace_shell.py` (update later in Task 18).

- [ ] **Step 1: Implement `deriveStage`** (pure function, easy to reason about):

```ts
export type Stage = "onboarding"|"clarify"|"review";
export function deriveStage(s:{ hasAnalysis:boolean; readinessScore:number; hasPreview:boolean }):Stage{
  if (s.hasPreview) return "review";
  if (s.hasAnalysis) return "clarify";
  return "onboarding";
}
```

- [ ] **Step 2: Verify** `npx -y tsc --noEmit`.
- [ ] **Step 3: Commit** `feat(ui): stage derivation for adaptive emphasis`.

### Task 5: AppShell layout + emphasis + responsive

**Files:** Create `components/shell/AppShell.tsx` (+`.module.css`);
Modify `components/WorkspaceShell.tsx`.

- [ ] **Step 1: `AppShell`** accepts `stage` + three render slots
  (`sidebar`,`chat`,`preview`). CSS grid: desktop 3 columns whose `flex`/`grid`
  fractions change by `stage` (chat hero in `clarify`, preview hero in `review`);
  active pane gets ring + full opacity, idle panes dim. Width transitions use
  `--ease-spring`. Breakpoints: ≥1024 three panes; 768–1023 hide preview, expose
  a "Preview · NN%" button that opens it as a drawer; <768 single column with a
  segmented Chat⇄Preview control + hamburger drawer for the sidebar. Use
  `transform`/`opacity` for transitions only.
- [ ] **Step 2: Rewire `WorkspaceShell.tsx`** to keep all existing state/effects
  but render `<AppShell stage={deriveStage(...)} sidebar={…} chat={…} preview={…}/>`
  with temporary placeholder content in each slot (real content lands in later
  phases). Remove the old `.workspace`/`analysis-empty-state` markup now; update
  `globals.css` to drop dead old classes.
- [ ] **Step 3: Verify** `npx -y tsc --noEmit`, `npm run build`. Manual: app loads,
  three panes visible, resizing the window collapses panes per breakpoints.
- [ ] **Step 4: Commit** `feat(ui): adaptive 3-pane responsive app shell`.

---

## Phase 2 — Sidebar (account, setup, projects, history)

### Task 6: Sidebar + AccountMenu

**Files:** Create `components/shell/Sidebar.tsx` (+`.module.css`),
`components/shell/AccountMenu.tsx`.

- [ ] **Step 1:** `Sidebar` renders logo, **New SAD** (accent button → resets to a
  fresh analysis session, reusing the existing "new" reset path), a Drive status
  row, slots for `SetupChecklist`/`ProjectList`/`SaveHistory`, and the account row
  at the bottom opening `AccountMenu`.
- [ ] **Step 2:** `AccountMenu` popover: identity (from auth user), Google Drive
  section (Connected + folder name from `getDriveRepoStatus`; **Open repo in
  Drive** using the repo url; **Disconnect Drive** → `disconnectDriveRepo`),
  **Sign out** (existing Firebase sign-out). Disconnect + Sign out are `danger`
  variant and visually separated. Match `sidebar-account.html`.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: menu opens, disconnect + sign-out
  call the right functions.
- [ ] **Step 4: Commit** `feat(ui): sidebar shell + account/drive menu`.

### Task 7: SetupChecklist + Drive banner

**Files:** Create `components/shell/SetupChecklist.tsx`; Modify `Sidebar.tsx`.

- [ ] **Step 1:** Render `✓ Signed in` (auth user present) and a Drive row that is
  `✓ Connected` or `○ Connect Drive "to save"` (amber) from `getDriveRepoStatus`.
  Clicking the Drive row triggers the existing connect flow.
- [ ] **Step 2:** Expose a reusable `<ConnectDriveBanner/>` (amber "Connect Google
  Drive to save your SAD & wiki" + Connect button) for the composer area; only
  shown when not connected. Wires to the existing connect function.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: states reflect real Drive status.
- [ ] **Step 4: Commit** `feat(ui): setup checklist + connect-drive banner`.

### Task 8: ProjectList + SaveHistory

**Files:** Create `components/shell/ProjectList.tsx`,
`components/shell/SaveHistory.tsx`; restyle `CreateProjectDialog.tsx`.

- [ ] **Step 1:** `ProjectList` from `listProjects`; active project highlighted
  (blue ring); click → `switchProject` then reload analysis/preview/history for it;
  "New project" opens the (restyled) `CreateProjectDialog` → `createProject`.
- [ ] **Step 2:** `SaveHistory` nested under the active project from
  `listProjectSaves`; each row shows save id + time + "Open ▸" (Doc url); loading
  uses `Skeleton`. Preserve the auth-restore re-fetch behavior.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: switch projects, history reloads,
  Open opens the Doc.
- [ ] **Step 4: Commit** `feat(ui): project switcher + per-project save history`.

---

## Phase 3 — Chat + Q&A

### Task 9: ChatThread + thinking indicator

**Files:** Create `components/chat/ChatThread.tsx` (+`.module.css`).

- [ ] **Step 1:** Render an ordered message list (assistant/user bubbles) derived
  from the analysis state (the user's typed problem, each `next_question`, and the
  answers recorded in `questionnaire.answers`). While an analysis request is
  in-flight, append a `ThinkingDots` bubble. Auto-scroll to newest.
- [ ] **Step 2:** Assistant question bubble shows `next_question.text` + a
  `why-this-matters` helper line (`next_question.why_this_matters`). Match `qna-chat.html`.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: a turn shows thinking dots then the
  next question.
- [ ] **Step 4: Commit** `feat(ui): chat thread with thinking indicator`.

### Task 10: Composer + AttachChips

**Files:** Create `components/chat/Composer.tsx` (+`.module.css`),
`components/chat/AttachChips.tsx`.

- [ ] **Step 1:** Composer = text input + 📎 attach button (opens file picker) +
  send button. On file pick → `uploadSources`; show a `loading` state on the
  attach button during upload.
- [ ] **Step 2:** `AttachChips` docks uploaded files as removable chips ABOVE the
  input (filename + "N chars read · SRC-id"), plus an "Add file" affordance; chips
  persist across turns (they are `source_references`); removing a chip drops it
  from the set sent on the next analyze call. Never render attachments as chat
  messages. Match `attach.html`. Accept TXT/MD/PDF/DOCX/XLSX/CSV.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: attach a file → chip appears above
  bar, persists, removable.
- [ ] **Step 4: Commit** `feat(ui): composer with docked attachment chips`.

### Task 11: AnswerChips + submit

**Files:** Create `components/chat/AnswerChips.tsx`; Modify `Composer.tsx`,
`ChatThread.tsx`.

- [ ] **Step 1:** When `next_question.choices` is non-empty, render tappable chips;
  `selection_mode==="multiple"` allows multi-select then a confirm; disabled
  choices use `is_disabled`/`status_label`. Selecting a chip (or typing free text)
  submits via the existing `analyzeRequirement` path, forwarding `analysisSessionId`.
- [ ] **Step 2:** Free text always allowed even when choices exist ("or type your
  own"). Preserve Guard-B / amend continuation behavior already in the data layer.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: tap a choice → it submits and the
  next question arrives; free-text also works.
- [ ] **Step 4: Commit** `feat(ui): tappable answer choices + free-text submit`.

### Task 12: ReadinessPane + CoverageChecklist

**Files:** Create `components/chat/ReadinessPane.tsx` (+`.module.css`),
`components/chat/CoverageChecklist.tsx`.

- [ ] **Step 1:** Right-pane content during `clarify`: a **readiness ring**
  (`readiness.score`/`label`/`confidence`) and `CoverageChecklist` from
  `categories[]` using the human `label` + ✓/◐/○ for `complete|partial|missing`,
  and a collapsible "What I understand so far" (`understanding_summary`). Pane is
  dimmed (idle) per emphasis. Match `qna-chat.html`.
- [ ] **Step 2:** At `readiness.score===100`, show the "ready to draft" assistant
  message + a `Generate SAD preview` Button that calls `generateSadPreview`
  (showing `PhaseStepper` phases Reading→Drafting→Finalising while in-flight) and
  moves stage to `review`.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: ring/coverage update each turn;
  100% reveals Generate with the phase stepper.
- [ ] **Step 4: Commit** `feat(ui): readiness ring, coverage, generate handoff`.

---

## Phase 4 — Preview, Save, Wiki

### Task 13: PreviewPane

**Files:** Create `components/preview/PreviewPane.tsx` (+`.module.css`).

- [ ] **Step 1:** Render from `SadPreviewResponse`: title, **Draft-ready** pill,
  **Temporary — not saved yet** pill (`temporary_notice`), `sections[]`
  (heading+body+per-section source refs), **Assumptions we made** (`assumptions`),
  **Questions to confirm with the business** (`open_questions`). Put the
  `it_readiness.checklist` behind a "Review readiness checklist ▾" expander — do
  not show a contradictory headline score. Preview is the hero in `review`. Match
  `sad-preview.html`.
- [ ] **Step 2:** Action bar: **Save to Drive** (primary), **Update wiki**
  (secondary), **Refine in chat** (ghost → return to `clarify`, focus composer).
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual: preview renders all sections; refine
  returns to chat.
- [ ] **Step 4: Commit** `feat(ui): SAD preview pane as hero`.

### Task 14: SaveFlow

**Files:** Create `components/preview/SaveFlow.tsx`; Modify `PreviewPane.tsx`,
`SaveHistory.tsx`.

- [ ] **Step 1:** Clicking Save runs `saveSadPreview`. Show `StepProgress`
  (Creating Google Doc… → Saving sources & manifest… → Saved ✓). On success show
  "Saved to <project> · <save_id> · Open in Drive" (`sad_doc.url`) and refresh
  `SaveHistory`. Keep idempotent-save behavior.
- [ ] **Step 2:** If `PROJECT_REQUIRED` (409) → open `CreateProjectDialog` inline,
  then retry; if Drive not connected → show connect, then retry. Surface stable
  error codes as plain inline messages with retry.
- [ ] **Step 3: Verify** `tsc`, `lint`. Manual (local mode): save → stepped
  progress → success + history entry; repeat save is idempotent.
- [ ] **Step 4: Commit** `feat(ui): stepped save-to-drive flow`.

### Task 15: WikiDialog

**Files:** Create `components/preview/WikiDialog.tsx` (+`.module.css`); restyle
from `WikiUpdateDialog.tsx` (then remove the old one).

- [ ] **Step 1:** "Update wiki" → `previewWikiUpdate`; render the 8 files with
  **new/updated/conflict** badges; `PhaseStepper` + "Updating N / 8 files…" during
  commit; "Back up & update" → `commitWikiUpdate`. Conflict-aware approval and the
  backup-before-overwrite messaging match `sad-preview.html`.
- [ ] **Step 2: Verify** `tsc`, `lint`. Manual (live mode optional): dialog lists
  files, commit shows progress.
- [ ] **Step 3: Commit** `feat(ui): wiki update dialog with phased progress`.

---

## Phase 5 — Onboarding, motion polish, test migration

### Task 16: WelcomeHero + onboarding

**Files:** Create `components/onboarding/WelcomeHero.tsx` (+`.module.css`);
Modify `WorkspaceShell.tsx`.

- [ ] **Step 1:** In `onboarding` stage (no analysis), the chat pane shows the
  welcome hero: mark, headline, 3 steps, **Continue with Google** (existing
  sign-in), and **"or just start typing →"** (guest via `createGuestDraft`).
  Sidebar shows the Setup checklist; preview shows the placeholder. After sign-in
  or first message, transition to `clarify`/working. Match `onboarding-merged.html`.
- [ ] **Step 2: Verify** `tsc`, `lint`, `build`. Manual: signed-out welcome, guest
  start, sign-in path.
- [ ] **Step 3: Commit** `feat(ui): merged onboarding welcome`.

### Task 17: Motion + responsive polish

**Files:** Modify `AppShell.module.css` and component CSS modules.

- [ ] **Step 1:** Add screen/stage crossfade + slight directional slide on stage
  change (`transform`/`opacity`, `--motion-mid`, exit faster than enter). Verify
  every async surface (analyze, generate, save, wiki, switch project, sign-in)
  shows its loading primitive.
- [ ] **Step 2:** Validate responsive: tablet preview drawer, mobile Chat⇄Preview
  segmented control + hamburger sidebar drawer; touch targets ≥44px; `min-h-dvh`;
  no horizontal scroll. Test at 375/768/1024/1440.
- [ ] **Step 3:** Verify `prefers-reduced-motion` reduces transitions (toggle OS
  setting); content still renders.
- [ ] **Step 4: Verify** `tsc`, `lint`, `build`. Manual: smooth transitions, all
  breakpoints.
- [ ] **Step 5: Commit** `feat(ui): stage transitions, reduced-motion, responsive polish`.

### Task 18: Migrate Python static UI tests + cleanup

**Files:** Modify `tests/test_mvp_*_ui.py`, `tests/test_mvp_workspace_shell.py`;
remove fully-migrated old components.

- [ ] **Step 1:** For each `test_mvp_*_ui.py`, rewrite assertions to the new
  structure with equivalent coverage. Example for `test_mvp_workspace_shell.py`:
  assert the new components exist (`shell/AppShell.tsx`, `chat/ChatThread.tsx`,
  `chat/ReadinessPane.tsx`, `preview/PreviewPane.tsx`), that `page.tsx` renders
  `WorkspaceShell`, and that key business-first copy is present (e.g. the welcome
  headline, "Questions to confirm with the business"). Do not assert on removed
  markers like `analysis-empty-state` / `ReadinessPanel`.
- [ ] **Step 2:** Update auth/drive/guest/qna/project/sad-preview/sad-save/source
  UI tests the same way (assert the new component file + a stable user-facing
  string each still guarantees). Keep them meaningful, not trivially true.
- [ ] **Step 3:** Delete migrated old panels (or keep thin re-export shims only if a
  test legitimately needs the filename). Ensure no dead imports remain.
- [ ] **Step 4: Verify** full gate:

```
npx -y tsc --noEmit
npm run lint
npm run build
# worktree root, local mode:
D:\GoogleCloudHack\.venv\Scripts\python.exe -m pytest -q
```
Expect: types clean, lint clean, build OK, full pytest green (UI static tests
updated; backend tests unchanged — still 471 + firestore).

- [ ] **Step 5: Commit** `refactor(ui): migrate static UI tests, remove old panels`.

---

## Manual Smoke (user-driven, after Task 17/18)

Drip-fed per screen against the mockups, backend in local mode + `npm run dev`:
1. Welcome → guest start / Google sign-in.
2. Q&A: thinking dots, tappable choices, attach chip docks above bar, readiness
   ring + coverage update, 100% reveals Generate with phase stepper.
3. Preview hero: sections/assumptions/open-questions; refine returns to chat.
4. Save: stepped progress → success + history; idempotent repeat.
5. Wiki dialog (optional live).
6. Projects: switch reloads; account menu disconnect/sign-out.
7. Responsive: 375/768/1024; reduced-motion.

## Stop Rules

- Any backend/`api.ts`-contract change required → STOP (design is frontend-only).
- A new runtime dependency seems needed → STOP and report (icons inline, font via next/font).
- A static UI test can only pass by deleting it → STOP (rewrite assertions instead).
- `tsc`/`build` cannot go green at a phase boundary → STOP and fix before next phase.

## Verification Summary Required Before Completion

```
tsc --noEmit clean; next lint clean; next build OK.
Full pytest green (backend unchanged; UI static tests updated).
Every async action shows a loading primitive (no blank waits).
Adaptive emphasis + responsive verified at 375/768/1024/1440.
prefers-reduced-motion honored.
No new runtime dependency added; backend/api.ts untouched.
Manual smoke 1–7 passed against the mockups.
```
