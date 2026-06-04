# `app/frontend` Structure and Backend Integration

This note analyzes only the `app/frontend` folder.

## 1. Frontend framework version and routing structure

### Framework

The frontend is a **Next.js 16.2.1** application using:

- `react` 19.2.4
- the **App Router** under `src/app`
- TypeScript
- Tailwind CSS 4

### Routing structure

The route structure is file-based through the App Router:

- `/` → [src/app/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/page.tsx )
- `/history` → [src/app/history/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/history/page.tsx )
- `/portfolio` → [src/app/portfolio/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/portfolio/page.tsx )

There are no route handlers in this folder. All backend interaction goes through the shared API client in `src/lib/api.ts`.

### Client/server boundary

- [src/app/layout.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/layout.tsx ) is a server component by default.
- The actual pages and interactive UI are client components (`"use client"`), including:
  - `src/app/page.tsx`
  - `src/app/history/page.tsx`
  - `src/app/portfolio/page.tsx`
  - most shared UI components

That means the frontend is intentionally client-driven rather than SSR-heavy.

## 2. Main pages, feature sections, and shared UI components

### Main pages

#### Home page: `/`

File:

- [src/app/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/page.tsx )

Main sections:

- sidebar with ticker selection
- workflow selection
- analysis launch button
- hero/marketing block
- live analysis panel

This is the primary realtime analysis surface.

#### History page: `/history`

File:

- [src/app/history/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/history/page.tsx )

Main sections:

- archive sidebar with saved analyses
- detail pane showing selected run
- per-ticker agent cards
- CIO decision cards
- markdown report viewer

#### Portfolio page: `/portfolio`

File:

- [src/app/portfolio/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/portfolio/page.tsx )

Main sections:

- portfolio editor sidebar
- cash input
- editable position list
- save button and refresh button
- portfolio summary cards
- per-ticker valuation table

### Shared UI components

Shared presentation components:

- `HeroBlock`
- `Navbar`
- `Sidebar`
- `SectionHeader`
- `StatBlock`
- `ReportCard`

Domain-facing components:

- `AnalysisPanel`
- `AnalysisCard`
- `CIOCard`
- `TickerSelector`
- `WorkflowSelector`

These are reused across pages to keep the UI consistent.

## 3. How the frontend fetches data and which backend endpoints it appears to call

### Fetch strategy

The frontend uses a very simple pattern:

- plain `fetch()`
- wrapped in helper functions in [src/lib/api.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/api.ts )
- local React state via `useState`
- `useEffect` for initial loads and polling
- no React Query, SWR, Redux, Zustand, or similar global store

### Backend proxying

The frontend is configured to call backend endpoints through Next rewrites:

- [next.config.ts]( /D:/TradingAgent-VN/app/frontend/next.config.ts )

It rewrites:

- `/api/:path*` → `http://localhost:8000/api/:path*`

So the browser talks to the Next app, and Next proxies API requests to the FastAPI backend.

### Backend endpoints actually used

From [src/lib/api.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/api.ts ):

- `GET /api/portfolio`
- `POST /api/portfolio`
- `GET /api/portfolio/value`
- `GET /api/market/prices?tickers=...`
- `GET /api/history`
- `GET /api/history/{id}`
- `POST /api/analyze`
- `GET /api/analyze/{job_id}`

### Which pages call which endpoints

#### Home page

- `TickerSelector` polls `GET /api/market/prices`
- `AnalysisPanel` creates a job via `POST /api/analyze`
- `AnalysisPanel` polls `GET /api/analyze/{job_id}`

#### History page

- `listHistory()` calls `GET /api/history`
- `getHistoryDetail()` calls `GET /api/history/{id}`

#### Portfolio page

- `getPortfolio()` calls `GET /api/portfolio`
- `savePortfolio()` calls `POST /api/portfolio`
- `getPortfolioValue()` calls `GET /api/portfolio/value`

### Backend endpoints not used by the current frontend pages

The frontend does not appear to call these backend routes from the inspected code:

- `GET /api/market/news`
- `POST /api/market/sync`

Those are backend capabilities, but not part of the current realtime UI flow.

## 4. State management patterns, data-fetching helpers, hooks, and client/server boundaries

### State management pattern

The app uses local component state only:

- `useState` for selected tickers, workflow, loading flags, portfolio fields, and fetched data
- `useEffect` for initial fetches and periodic polling
- `useRef` in `AnalysisPanel` to avoid stale callbacks
- `usePathname` in `Navbar` for active-nav styling

There is no centralized state manager.

### Data-fetching helpers

All backend requests are centralized in:

- [src/lib/api.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/api.ts )

That file is the only place that knows the concrete backend routes.

### Hook usage by feature

- `TickerSelector` polls prices every 30 seconds.
- `AnalysisPanel` starts a job once, then polls every second until done.
- `history/page.tsx` loads the archive list on mount and fetches details on click.
- `portfolio/page.tsx` loads the saved portfolio and portfolio value on mount, then refreshes on demand.

### Client/server boundary

The interactive pages and most components are client components.

Server component usage is limited to:

- the root layout

That is a deliberate fit for a realtime dashboard-style UI.

## 5. View components vs domain-specific UI logic

### Mostly view/presentation components

These are mostly visual wrappers:

- `HeroBlock`
- `Navbar`
- `Sidebar`
- `SectionHeader`
- `StatBlock`
- `ReportCard`

They format content and provide the design system.

### Domain-specific UI logic

These components embed product behavior and should be read as application logic, not just styling:

- `AnalysisPanel`
  - starts jobs
  - polls progress
  - tracks phases and completion
- `AnalysisCard`
  - maps agent state to status badges and output display
- `CIOCard`
  - shows recommendation, confidence, and debate summary
- `TickerSelector`
  - fetches live prices and manages ticker selection
- `WorkflowSelector`
  - maps workflow choices to business workflows
- `portfolio/page.tsx`
  - edits portfolio state
  - saves the JSON payload
  - computes valuation through backend
- `history/page.tsx`
  - loads and drills into analysis history

## 6. How user interactions map to backend analysis workflows or portfolio/history features

### Home page workflow

User interaction:

1. choose one or more tickers
2. choose a workflow
3. click `Phân tích`

Frontend behavior:

1. `page.tsx` updates local state
2. `AnalysisPanel` calls `POST /api/analyze`
3. backend creates an async job
4. `AnalysisPanel` polls `GET /api/analyze/{job_id}`
5. as the backend job advances, the UI shows:
   - agent cards
   - CIO cards
   - final report

This is the frontend’s primary path into the backend analysis engine.

### History workflow

User interaction:

1. open `/history`
2. select an archived run from the sidebar

Frontend behavior:

1. fetch the analysis index from `GET /api/history`
2. fetch a chosen analysis from `GET /api/history/{id}`
3. render the saved agent outputs, CIO output, and markdown report

This is a read-only replay of the backend’s persisted analysis snapshots.

### Portfolio workflow

User interaction:

1. open `/portfolio`
2. edit cash and positions
3. save portfolio
4. refresh valuation

Frontend behavior:

1. load existing portfolio from `GET /api/portfolio`
2. persist edits via `POST /api/portfolio`
3. compute live valuation via `GET /api/portfolio/value`

This page is the UI surface for the backend’s portfolio JSON and price lookup logic.

### Live price display

`TickerSelector` polls `GET /api/market/prices` in the background so the home page can show current prices while the user is selecting tickers.

## 7. Minimum files to read to understand the frontend end-to-end

If you want the smallest useful reading set, read these files first:

1. [next.config.ts]( /D:/TradingAgent-VN/app/frontend/next.config.ts )
2. [src/lib/api.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/api.ts )
3. [src/lib/types.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/types.ts )
4. [src/app/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/page.tsx )
5. [src/components/AnalysisPanel.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/AnalysisPanel.tsx )
6. [src/app/history/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/history/page.tsx )
7. [src/app/portfolio/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/portfolio/page.tsx )
8. [src/components/Navbar.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/Navbar.tsx )
9. [src/components/AnalysisCard.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/AnalysisCard.tsx )
10. [src/components/CIOCard.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/CIOCard.tsx )
11. [src/components/ReportCard.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/ReportCard.tsx )

That set covers:

- routing
- backend calls
- request/response shapes
- analysis job flow
- archive viewing
- portfolio editing and valuation

## 8. Exact next-file reading order for a human

1. [app/frontend/next.config.ts]( /D:/TradingAgent-VN/app/frontend/next.config.ts )
2. [app/frontend/src/lib/api.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/api.ts )
3. [app/frontend/src/lib/types.ts]( /D:/TradingAgent-VN/app/frontend/src/lib/types.ts )
4. [app/frontend/src/app/layout.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/layout.tsx )
5. [app/frontend/src/components/Navbar.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/Navbar.tsx )
6. [app/frontend/src/app/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/page.tsx )
7. [app/frontend/src/components/TickerSelector.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/TickerSelector.tsx )
8. [app/frontend/src/components/WorkflowSelector.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/WorkflowSelector.tsx )
9. [app/frontend/src/components/AnalysisPanel.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/AnalysisPanel.tsx )
10. [app/frontend/src/components/AnalysisCard.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/AnalysisCard.tsx )
11. [app/frontend/src/components/CIOCard.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/CIOCard.tsx )
12. [app/frontend/src/components/ReportCard.tsx]( /D:/TradingAgent-VN/app/frontend/src/components/ReportCard.tsx )
13. [app/frontend/src/app/history/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/history/page.tsx )
14. [app/frontend/src/app/portfolio/page.tsx]( /D:/TradingAgent-VN/app/frontend/src/app/portfolio/page.tsx )

If you want the shortest path, read files 1 through 10 first.
