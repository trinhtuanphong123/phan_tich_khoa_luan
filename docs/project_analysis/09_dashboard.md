# dashboard subsystem

`dashboard/` is a Next.js 16 App Router application that presents the repository’s backtest artifacts, workflow explanations, and market playback views. It is not a remote backend; it reads local files and a local SQLite database through server-side loaders and route handlers, then renders interactive client components on top.

## 1. Frontend structure and entry pages

- Framework stack: Next.js 16.2.1, React 19.2.4, Tailwind CSS 4, `better-sqlite3`, `lightweight-charts`, and `react-markdown`.
- Routing model: App Router under `src/app`; page files are server components by default, while the interactive dashboards are implemented in `"use client"` components.
- Root shell: `src/app/layout.tsx` wraps every page with `PlaybackProvider`, shared fonts, global styles, and the navbar.
- Main entry pages:
  - `src/app/page.tsx` is the home/overview page.
  - `src/app/leaderboard/page.tsx` is the strategy comparison page.
  - `src/app/portfolio/page.tsx` is the portfolio playback page.
  - `src/app/trading-view/page.tsx` is the price chart and execution-marker page.
  - `src/app/agents/page.tsx` is the workflow/analysis explanation page.
  - `src/app/blogs/page.tsx` is the report archive page.
  - `src/app/about/page.tsx` is the project narrative page.
- Shared route-level API surface:
  - `src/app/api/analysis/route.ts`
  - `src/app/api/benchmark/route.ts`
  - `src/app/api/candles/route.ts`
  - `src/app/api/candles-debug/route.ts`
  - `src/app/api/prices/route.ts`
  - `src/app/api/tickers/route.ts`

## 2. Data sources and artifact folders

The dashboard reads from two main local roots:

- `../backtest_results/`, relative to the `dashboard/` working directory.
- `../data/vnstock.db`, the local market-data SQLite database.

Within `backtest_results/`, the loaders expect these artifact families:

- `state/*.json` for per-workflow portfolio state.
- `blog_posts/*.md` for daily report markdown.
- `ledgers/YYYY-MM-DD/*.json` for per-day workflow ledgers.
- `cognitive/state/portfolio.json` for the cognitive workflow state snapshot.
- `cognitive/state/benchmark_metrics.json` for cognitive benchmark metadata.
- `cognitive/equity_curve.json` for the cognitive equity curve.
- `cognitive/ledgers/YYYY-MM-DD.json` for cognitive execution events.
- `cognitive/daily/{date}/analysis/{ticker}/cards.json` for analysis cards.
- `cognitive/daily/{date}/analysis/{ticker}/cio_decision.json` for CIO output.
- `cognitive/daily/{date}/normalized/workflow_artifact.json` for the normalized cognitive artifact shape.
- `{date}/{ticker}/{workflow}/tier3_cio_decision.json` and `tier2_debate_transcript.txt` for legacy workflow-specific artifacts.
- `{date}/normalized/{workflow}_workflow_artifact.json` for legacy normalized workflow artifacts.
- `evaluation/{workflow}/summary.json` for workflow summary metrics.

One additional comparison file is used when present:

- `../evaluation_engine/outputs/workflow_metrics/workflow_comparison.json`

The SQLite database at `../data/vnstock.db` must expose `market_data_daily`, which the dashboard uses for:

- `api/tickers` to list the allowed tradable tickers.
- `api/prices` to fetch latest closes.
- `api/candles` and `api/candles-debug` to build daily OHLCV series.
- `api/benchmark` to fetch VN30 or VNINDEX benchmark data.

## 3. Main dashboard features

- Leaderboard:
  - Compares the workflows on a shared playback cutoff.
  - Shows equity, return, P&L, win rate, Sharpe, drawdown, volatility, profit factor, and trade count.
  - Clicking a row navigates to `trading-view?workflow=...`.
- Portfolio playback:
  - Lets the user choose a workflow.
  - Shows equity history, a benchmark comparison chart, current NAV, cash, and position weights.
  - Fetches current prices and benchmark series from the local API routes.
- Trading view:
  - Lets the user choose a ticker and a timeframe.
  - Renders candlesticks, volume, moving averages, Bollinger bands, RSI, MACD, and buy/sell markers.
  - Highlights execution markers by workflow code and profitability.
- Workflow/analysis view:
  - Shows structured analysis cards, thought traces, CIO decisions, and fallback/legacy artifacts.
  - Uses the `workflow` query parameter to switch between Cognitive and the baseline workflows.
- Report archive:
  - Renders markdown reports grouped by date and workflow.
  - Uses lazy loading to page through a potentially large artifact archive.
- Home and about pages:
  - Provide the project overview, key KPIs, and thesis narrative.

## 4. How data is loaded, transformed, and displayed

The dashboard uses a layered data path rather than a single monolithic store.

1. Server-side loaders in `src/lib/data.ts` walk the filesystem, collect JSON/Markdown artifacts, and normalize them into typed structures.
2. `src/lib/summary-loader.cjs` reads workflow summaries from `evaluation/{workflow}/summary.json` and can override metrics using the thesis comparison file when it exists.
3. `src/lib/analysis-loader.cjs` is a legacy helper for older per-workflow artifact layouts; the modern runtime path is implemented in `src/lib/data.ts`.
4. `src/lib/compute.ts` derives leaderboard metrics from portfolio state and ledgers, including return, volatility, max drawdown, profit factor, and win-rate fields.
5. Route handlers under `src/app/api/*` expose the local file/SQLite data as JSON endpoints.
6. Client components fetch or receive that data and render the interactive UI:
   - `LeaderboardClient` computes a date-cutoff snapshot and sorts workflows by return.
   - `PortfolioClient` fetches prices and benchmark data, then derives position weights from the selected state.
   - `TradingViewClient` fetches tickers and candles, then converts ledger entries into chart markers.
   - `AgentsClient` fetches analysis artifacts and renders cards, CIO intent, and debate transcripts.
   - `BlogFeed` groups report markdown by date and feeds it into `BlogCard`, which renders markdown with `react-markdown`.
7. Playback dates are shared through `PlaybackContext`; pages seed the timeline with `PlaybackInit`.

## 5. Generic UI code vs domain-specific logic

### Mostly generic UI / presentation

- `src/components/Navbar.tsx`
- `src/components/PlaybackInit.tsx`
- `src/components/PlaybackSlider.tsx`
- `src/components/BlogCard.tsx`
- `src/lib/format.ts`
- `src/components/LightweightChart.tsx`
- `src/components/LightweightChart_CONTAINER.tsx`
- `src/components/LegendBox.tsx`

### Domain-specific analytics / report rendering

- `src/lib/data.ts`
- `src/lib/compute.ts`
- `src/lib/summary-loader.cjs`
- `src/lib/analysis-loader.cjs`
- `src/app/api/analysis/route.ts`
- `src/app/api/benchmark/route.ts`
- `src/app/api/candles/route.ts`
- `src/app/api/prices/route.ts`
- `src/app/api/tickers/route.ts`
- `src/components/LeaderboardClient.tsx`
- `src/components/PortfolioClient.tsx`
- `src/components/TradingViewClient.tsx`
- `src/components/AgentsClient.tsx`
- `src/components/BlogFeed.tsx`
- `src/components/CandlestickChart.tsx`

## 6. Assumptions about local paths, build environment, and generated artifacts

- The app assumes it is launched from the `dashboard/` directory, because file paths are built with `process.cwd()` and `../...` joins.
- The workspace must contain a sibling `backtest_results/` directory and a sibling `data/vnstock.db` file.
- `better-sqlite3` is a native dependency, so the runtime environment must support local native module installation and execution.
- `npm run dev` starts Next.js on `0.0.0.0:8000`, not the default `3000`.
- `loadBlogPosts()` expects filenames in the form `YYYY-MM-DD_<workflow>_Daily_Report.md`.
- `loadStates()` expects one JSON file per workflow in `backtest_results/state/`, plus the cognitive state at `backtest_results/cognitive/state/portfolio.json`.
- `loadLedgersForDate()` expects per-day ledger folders in `backtest_results/ledgers/YYYY-MM-DD/`.
- `loadDailyAnalysis()` prefers normalized cognitive artifacts, but still supports legacy paths.
- `loadWorkflowTickerAnalysis()` prefers normalized per-workflow artifacts, but falls back to legacy per-ticker directories.

## 7. File priority map

### Must-understand

- `dashboard/package.json`
- `dashboard/src/app/layout.tsx`
- `dashboard/src/app/page.tsx`
- `dashboard/src/contexts/PlaybackContext.tsx`
- `dashboard/src/lib/data.ts`
- `dashboard/src/lib/compute.ts`
- `dashboard/src/lib/summary-loader.cjs`
- `dashboard/src/app/api/analysis/route.ts`
- `dashboard/src/app/api/benchmark/route.ts`
- `dashboard/src/app/api/candles/route.ts`
- `dashboard/src/app/api/prices/route.ts`
- `dashboard/src/app/api/tickers/route.ts`
- `dashboard/src/components/LeaderboardClient.tsx`
- `dashboard/src/components/PortfolioClient.tsx`
- `dashboard/src/components/TradingViewClient.tsx`
- `dashboard/src/components/CandlestickChart.tsx`
- `dashboard/src/components/AgentsClient.tsx`
- `dashboard/src/components/BlogFeed.tsx`

### Read later

- `dashboard/tsconfig.json`
- `dashboard/next.config.ts`
- `dashboard/src/app/leaderboard/page.tsx`
- `dashboard/src/app/portfolio/page.tsx`
- `dashboard/src/app/trading-view/page.tsx`
- `dashboard/src/app/agents/page.tsx`
- `dashboard/src/app/blogs/page.tsx`
- `dashboard/src/app/about/page.tsx`
- `dashboard/src/components/BlogCard.tsx`
- `dashboard/src/components/Navbar.tsx`
- `dashboard/src/components/PlaybackInit.tsx`
- `dashboard/src/components/PlaybackSlider.tsx`
- `dashboard/src/lib/format.ts`
- `dashboard/src/components/LightweightChart.tsx`
- `dashboard/src/components/LightweightChart_CONTAINER.tsx`
- `dashboard/src/components/LegendBox.tsx`
- `dashboard/src/app/api/candles-debug/route.ts`
- `dashboard/src/lib/analysis-loader.cjs`
- `dashboard/src/lib/data.test.cjs`
- `dashboard/src/lib/analysis-loader.test.cjs`
- `dashboard/src/lib/summary-loader.test.cjs`
- `dashboard/src/components/PortfolioClient.test.cjs`

### Low priority

- `dashboard/README.md`
- `dashboard/postcss.config.mjs`
- `dashboard/eslint.config.mjs`
- `dashboard/tailwind.config.ts`
- `dashboard/.gitignore`
- `dashboard/public/*`
- `dashboard/src/app/favicon.ico`

## 8. Exact next-file reading order

1. `dashboard/package.json`
2. `dashboard/tsconfig.json`
3. `dashboard/src/app/layout.tsx`
4. `dashboard/src/contexts/PlaybackContext.tsx`
5. `dashboard/src/lib/data.ts`
6. `dashboard/src/lib/summary-loader.cjs`
7. `dashboard/src/lib/compute.ts`
8. `dashboard/src/lib/format.ts`
9. `dashboard/src/app/api/tickers/route.ts`
10. `dashboard/src/app/api/candles/route.ts`
11. `dashboard/src/app/api/prices/route.ts`
12. `dashboard/src/app/api/benchmark/route.ts`
13. `dashboard/src/app/api/analysis/route.ts`
14. `dashboard/src/app/page.tsx`
15. `dashboard/src/components/LeaderboardClient.tsx`
16. `dashboard/src/app/leaderboard/page.tsx`
17. `dashboard/src/components/PortfolioClient.tsx`
18. `dashboard/src/app/portfolio/page.tsx`
19. `dashboard/src/components/TradingViewClient.tsx`
20. `dashboard/src/components/CandlestickChart.tsx`
21. `dashboard/src/components/LightweightChart.tsx`
22. `dashboard/src/app/trading-view/page.tsx`
23. `dashboard/src/components/AgentsClient.tsx`
24. `dashboard/src/app/agents/page.tsx`
25. `dashboard/src/components/BlogFeed.tsx`
26. `dashboard/src/components/BlogCard.tsx`
27. `dashboard/src/app/blogs/page.tsx`
28. `dashboard/src/app/about/page.tsx`
29. `dashboard/src/components/Navbar.tsx`
30. `dashboard/src/components/PlaybackInit.tsx`
31. `dashboard/src/components/PlaybackSlider.tsx`
32. `dashboard/src/components/LightweightChart_CONTAINER.tsx`
33. `dashboard/src/components/LegendBox.tsx`
34. `dashboard/src/app/api/candles-debug/route.ts`
35. `dashboard/src/lib/analysis-loader.cjs`

