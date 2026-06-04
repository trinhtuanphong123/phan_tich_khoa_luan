# `config.py` Configuration Spine

This note analyzes `config.py` only.

## 1. Configuration domains in this repo

`config.py` organizes settings into a small number of runtime domains:

### Trading

`TradingConfig` defines the trading simulator and portfolio defaults:

- `portfolio_cash`
- `lot_size`
- `settlement_lag_days`
- `buy_fee_rate`
- `sell_fee_rate`
- `max_trade_pct`
- `max_buys_per_ticker`

### Strategy thresholds

`StrategyThresholds` holds signal-generation and heuristic thresholds:

- `price_change_threshold`
- `vol_ratio_threshold`
- `news_min_count`
- `alpha_threshold`
- `sell_threshold_offset`
- `atr_scale`
- `weight_alpha`
- `weight_beta`
- `weight_increment_buffer_pct`
- `news_lookback_days`

### Risk limits

`RiskLimits` centralizes guardrails used by backtests and CIO-style decisions:

- `max_position_pct`
- `max_portfolio_invested_pct`
- `stop_loss_pct`
- `max_drawdown_pct`
- `max_sector_exposure_pct`
- `min_cash_reserve_pct`

### Workflow weights

`WorkflowWeights` configures score and sizing behavior for workflows:

- `trad_target_weight`
- `kelly_min_weight_pct`
- `kelly_max_weight_pct`

### Model routing

`ModelConfig` determines the model names and proxy connection settings:

- `primary_model`
- `financial_model`
- `news_model`
- tier 2 model selectors:
  - `t2_macro_model`
  - `t2_news_model`
  - `t2_financial_model`
  - `t2_technical_model`
  - `t2_quant_model`
- tier 3 model selectors:
  - `t3_debate_model`
  - `t3_argument_model`
- tier 4 / CIO:
  - `t4_cio_model`
- daily report:
  - `daily_report_model`
- runtime concurrency:
  - `llm_concurrency`
- proxy credentials:
  - `cliproxy_base_url`
  - `cliproxy_api_key`

### Path configuration

`PathConfig` defines the filesystem layout:

- `data_dir`
- `vnstock_db_path`
- `news_db_path`
- `cognitive_db_path`
- `market_db_path`
- `backtest_results_dir`
- `rag_storage_dir`
- `analysis_reports_dir`

## 2. Which variables affect multiple subsystems

Some settings are not confined to one feature area and influence several parts of the system.

### `DATA_DIR`

This is the base storage root. It affects where runtime artifacts live and indirectly shapes many dependent paths.

### `VNSTOCK_DB_PATH`

Used for market OHLCV data. It matters for:

- crawlers
- backtests
- market-price lookup
- realtime analysis

### `NEWS_DB_PATH`

Used by news crawling, news analysis, and the agent stack that consumes news signals.

### `COGNITIVE_DB_PATH`

Used by cognitive trading memory/state features. It affects cognitive workflows and any history/memory-dependent runs.

### `BACKTEST_RESULTS_DIR`

Shared by backtest output and the research dashboard.

### `WORKDIR`

This is the RAG storage root. It affects indexing, querying, and any RAG-backed agent analysis.

### `ANALYSIS_REPORTS_DIR`

This determines where generated financial analysis reports land, which can then be reused by later workflows or inspected manually.

### `PRIMARY_MODEL`, `FINANCIAL_MODEL`, `NEWS_MODEL`

These route core agent behavior and can affect multiple analysis stages.

### `T2_*`, `T3_*`, `T4_CIO`, `DAILY_REPORT`

These are tiered model selectors that influence specialist agents, debate, CIO synthesis, and daily reporting.

### `CLIPROXY_BASE_URL`, `CLIPROXY_API_KEY`

These affect every model call routed through the proxy. If these are wrong, multiple subsystems fail at once.

### Risk limits and strategy thresholds

Most of these are consumed by backtesting and decision logic, but they also shape how recommendations are interpreted in analysis and CIO output.

## 3. Which settings are required to run minimal workflows

The repo is designed with sensible defaults, so a minimal run can work with relatively few explicit environment variables. The most important practical distinction is between "defaults exist" and "you must override this for your environment."

### Minimal local execution with defaults

For the code paths in `config.py`, the following can run with defaults if the repository layout matches the expected paths:

- `DATA_DIR`
- `VNSTOCK_DB_PATH`
- `NEWS_DB_PATH`
- `COGNITIVE_DB_PATH`
- `BACKTEST_RESULTS_DIR`
- `WORKDIR`
- `ANALYSIS_REPORTS_DIR`

If unset, they fall back to repository-relative locations.

### Minimal workflow that still needs external service config

To actually run analysis workflows that call LLM-backed components, the practical minimum is:

- `CLIPROXY_BASE_URL`
- `CLIPROXY_API_KEY`
- at least one usable model name, usually `PRIMARY_MODEL`

Without those, agent analysis and report generation are likely to fail or fall back incorrectly.

### Minimal workflow that touches trading logic

For trading/backtest runs, the defaults in `TradingConfig`, `StrategyThresholds`, `RiskLimits`, and `WorkflowWeights` are sufficient in principle if the user accepts the built-in assumptions.

That means a minimal backtest can often run without setting any of:

- `PORTFOLIO_CASH`
- `LOT_SIZE`
- `BUY_FEE_RATE`
- `SELL_FEE_RATE`
- `MAX_TRADE_PCT`
- `MAX_POSITION_PCT`
- `STOP_LOSS_PCT`

But if the user wants realistic behavior for their strategy or broker assumptions, those should be tuned.

## 4. Which settings are risky or easy to misconfigure

### Path settings

These are easy to misconfigure because a wrong value silently changes where data is written or read from:

- `DATA_DIR`
- `VNSTOCK_DB_PATH`
- `NEWS_DB_PATH`
- `COGNITIVE_DB_PATH`
- `BACKTEST_RESULTS_DIR`
- `WORKDIR`
- `ANALYSIS_REPORTS_DIR`

Risks:

- data gets written to the wrong folder
- dashboards appear empty because they point at a different artifact directory
- RAG indexing runs but query results look missing because storage is not where you expect

### Proxy and model settings

These are the highest-risk settings because they can break the whole AI layer:

- `CLIPROXY_BASE_URL`
- `CLIPROXY_API_KEY`
- `PRIMARY_MODEL`
- `FINANCIAL_MODEL`
- `NEWS_MODEL`
- `T2_*`
- `T3_*`
- `T4_CIO`
- `DAILY_REPORT`

Risks:

- wrong endpoint
- invalid credential
- incompatible model name
- one tier working while another silently fails

### Percentage fields with unit conversion

`_env_pct()` treats values in `(0, 1]` as fractions and multiplies them by 100.

That means these are easy to misconfigure if you are not careful about units:

- `MAX_TRADE_PCT`
- `MAX_POSITION_PCT`
- `MAX_PORTFOLIO_INVESTED_PCT`
- `STOP_LOSS_PCT`
- `MAX_DRAWDOWN_PCT`
- `MAX_SECTOR_EXPOSURE_PCT`
- `MIN_CASH_RESERVE_PCT`

Examples of the risk:

- entering `0.15` may be interpreted as `15.0`
- entering `15` stays `15`
- a wrong mental model can create a portfolio that is far too aggressive or far too constrained

### Trading assumptions

These are especially sensitive in backtests:

- `PORTFOLIO_CASH`
- `LOT_SIZE`
- `SETTLEMENT_LAG_DAYS`
- `BUY_FEE_RATE`
- `SELL_FEE_RATE`
- `MAX_BUYS_PER_TICKER`

Risks:

- unrealistic P&L
- incorrect fill sizing
- incompatible trade frequency
- misleading backtest metrics

### Strategy thresholds

These can quietly change signal behavior:

- `PRICE_CHANGE_THRESHOLD`
- `VOL_RATIO_THRESHOLD`
- `NEWS_MIN_COUNT`
- `ALPHA_THRESHOLD`
- `SELL_THRESHOLD_OFFSET`
- `ATR_SCALE`
- `WEIGHT_ALPHA`
- `WEIGHT_BETA`
- `WEIGHT_INCREMENT_BUFFER_PCT`
- `NEWS_LOOKBACK_DAYS`

Risks:

- too many false positives
- no trades at all
- news signals dominating or disappearing
- backtests that look good only because thresholds are overfit

## Practical summary

`config.py` is the repo’s runtime spine:

- it defines where persistent data lives
- it routes all LLM/model calls
- it encodes trading and risk assumptions
- it determines how the different workflows share artifacts

If you only remember a few things, remember these:

1. Path variables control whether the system is looking at the right data.
2. Proxy/model variables control whether the AI layer works at all.
3. Percentage settings are unit-sensitive and easy to misread.
4. Defaults are permissive, but they are not always realistic.
