# cognitive_trading subsystem

`cognitive_trading/` is the standalone cognitive backtest and decision-orchestration layer. It builds a ref-date-safe market/news context, runs a multi-agent analyst swarm, optionally debates conflicts, synthesizes a CIO decision, applies deterministic risk controls, persists daily artifacts, and then performs post-run reflection and playbook promotion.

## 1. Main orchestration entry files and major modules

### Entry points

- `cognitive_trading/runner.py` is the main CLI and backtest loop.
- `cognitive_trading/config.py` is the subsystem config spine. It derives paths, model names, and risk/trading thresholds from the root `config.py`.

### Planning / context

- `cognitive_trading/planner/event_ledger.py` builds the ref-date-safe event ledger.
- `cognitive_trading/planner/context_packer.py` turns the ledger into per-ticker agent contexts.
- `cognitive_trading/planner/planner_agent.py` routes each ticker into the normal or high-impact analyst set.

### Swarm / analyst layer

- `cognitive_trading/swarm/base_analyst.py` implements the shared ReAct loop and tool invocation pattern.
- Concrete analyst modules:
  - `cognitive_trading/swarm/macro_analyst.py`
  - `cognitive_trading/swarm/news_analyst.py`
  - `cognitive_trading/swarm/technical_analyst.py`
  - `cognitive_trading/swarm/quant_analyst.py`
  - `cognitive_trading/swarm/financial_analyst.py`

### Decision layer

- `cognitive_trading/decision/debate_trigger.py` decides when conflict or uncertainty should trigger debate.
- `cognitive_trading/decision/debate_engine.py` runs the bull/bear/judge debate and produces structured debate output.
- `cognitive_trading/decision/cio_agent.py` synthesizes the final intent ticket.
- `cognitive_trading/decision/risk_kernel.py` converts intent into executable orders and enforces hard constraints.

### Governance

- `cognitive_trading/governance/schemas.py` defines the strict Pydantic contracts for cards, intents, orders, and normalized artifacts.
- `cognitive_trading/governance/schema_validator.py` repairs raw analyst output into a valid `AnalysisCard`.
- `cognitive_trading/governance/confidence_calibrator.py` calibrates raw confidence using historical calibration data.

### Memory / learning

- `cognitive_trading/memory/db.py` bootstraps the SQLite memory database and owns the shared connection wrapper.
- `cognitive_trading/memory/episodic_store.py` stores episodes and updates horizon outcomes.
- `cognitive_trading/memory/calibration_store.py` tracks agent-sector win rates.
- `cognitive_trading/memory/strategy_store.py` stores playbooks.
- `cognitive_trading/memory/promotion_engine.py` promotes and demotes playbooks.
- `cognitive_trading/memory/reflection_agent.py` evaluates matured episodes, updates calibration, and writes the reflection summary.

### Reporting

- `cognitive_trading/reporting/daily_reporter.py` renders the daily Markdown report.

## 2. Lifecycle of a cognitive trading run

The run path is deterministic at the top level, with LLM calls only inside analyst/debate/CIO/reporting substeps.

1. `runner.py` parses `--tickers`, `--start`, and `--end`.
2. `CognitiveBacktestRunner` is constructed with `CognitiveConfig`.
3. The runner opens or initializes the memory DB at `data/cognitive.db` by default, loads the backtest portfolio state, loads any prior equity curve, and ensures output directories exist under `backtest_results/cognitive/`.
4. For each trading day between `start` and `end`:
   - It builds a market/news event ledger with `EventLedgerBuilder`.
   - It derives per-ticker contexts with `ContextPacker`.
   - It routes each ticker with `PlannerAgent`.
   - It runs the selected analysts through the shared ReAct loop.
   - It validates and calibrates each analyst output into an `AnalysisCard`.
   - It runs the debate engine to produce structured conflict resolution.
   - It asks the CIO agent for the final `IntentTicket`.
   - It runs the risk kernel to convert intent into an executable `OrderTicket` or a block.
   - It executes approved orders against the in-memory portfolio.
   - It builds the day summary, normalized artifact envelope, risk report, and daily Markdown report.
   - It persists the day’s JSON artifacts, portfolio snapshot, ledgers, equity point, and run status.
   - It stores episodic memory for any approved trades.
5. After the date loop ends, it:
   - evaluates matured episodes for `t+1`, `t+3`, `t+5`, and optionally `t+20`,
   - updates calibration rows from realized outcomes,
   - generates the reflection summary,
   - scans for promotable playbooks,
   - demotes failing playbooks,
   - computes benchmark metrics,
   - persists memory summaries and playbook summaries.

The key output is a complete artifact tree under `backtest_results/cognitive/`, plus the memory SQLite database.

## 3. How agent roles are represented and coordinated

The swarm is role-based rather than generic.

- `PlannerAgent` decides whether a ticker is `normal` or `high_impact`.
- Normal tickers run `technical` and `quant`.
- High-impact tickers run `macro`, `technical`, `quant`, `news`, and `financial`.
- `BaseAnalyst` gives every analyst the same ReAct control loop, tool interface, prompt format, and final-answer constraints.
- Each concrete analyst provides only the role-specific tools and model selection:
  - `MacroAnalyst` reads macro context and tracking-news summaries.
  - `NewsAnalyst` reads ticker-specific news context and tracking-news summaries.
  - `TechnicalAnalyst` uses technical indicators and alpha context.
  - `QuantAnalyst` uses factor / alpha diagnostics.
  - `FinancialAnalyst` reads cached financial-report context.
- The analyst outputs are normalized into `AnalysisCard` objects.
- `DebateEngine` turns a conflicting or uncertain card set into a bull/bear/judge result.
- `CIOAgent` synthesizes the final intent from cards, debate output, memory, and playbooks.
- `RiskKernel` turns the intent into an executable order or a block.

## 4. Memory, state, governance, and risk constraints

### Memory and state

- `memory/db.py` creates `episodic_memory`, `calibration_store`, and `strategy_memory` in the cognitive SQLite database.
- `EpisodicStore` stores approved trades, joins them to later outcomes, and retrieves prior sessions without lookahead.
- `CalibrationStore` updates per-agent/per-sector correctness.
- `StrategyStore` persists active and frozen playbooks.
- `PromotionEngine` promotes patterns from profitable episodes and demotes playbooks after repeated negative-alpha matches.
- `ReflectionAgent` matures episodes after enough trading days have elapsed and writes a human-readable reflection summary.

### Governance

- `schemas.py` enforces strict Pydantic contracts for:
  - `AnalysisCard`
  - `IntentTicket`
  - `OrderTicket`
  - `NormalizedAgentArtifact`
  - `WorkflowTickerArtifact`
  - `WorkflowArtifactEnvelope`
- `SchemaValidator` repairs malformed analyst output before it becomes a card.
- `ConfidenceCalibrator` blends raw confidence with historical calibration history.

### Risk

- `RiskKernel` is the hard constraint layer.
- It enforces:
  - maximum position size,
  - minimum cash reserve,
  - stop-loss exits,
  - drawdown halts,
  - sector exposure caps,
  - board-lot sizing,
  - settled-share constraints for sells.
- It also builds the daily risk report that gets written to the artifacts.

### Debate trigger

- `should_trigger_debate()` is the conflict / uncertainty policy helper.
- The current runner still runs debate for each ticker so the CIO always has a final debate score path, but the trigger module is the reusable policy definition.

## 5. Dependencies and connected surfaces

### On `vnstock/`

`cognitive_trading` is deeply coupled to `vnstock` for data access, indicators, portfolio simulation, and LLM plumbing:

- `DataRepository` for price history and sector lookup
- `MarketToolkit` for price and market context
- `QuantToolkit` for factor and technical diagnostics
- `SearchToolkit` for news and macro retrieval
- `FinancialAgent` for financial-report context
- `Portfolio`, `Position`, `BenchmarkAnalyzer`, and backtest trading-calendar helpers
- `vnstock.agents.prompting.Action` and `normalize_action`
- `vnstock.core.llm.call_llm`, `LLMError`, and the shared LLM session lifecycle
- `vnstock.workflows.debate.autogen_debate.run_autogen_debate`

### On root `config.py`

`cognitive_trading/config.py` is not independent. It imports shared root settings:

- `config.trading`
- `config.models`
- `config.risk_limits`
- `config.paths`

The important defaults are:

- `memory_db_path` -> `data/cognitive.db`
- `output_root` -> `backtest_results/cognitive`

### On `data/cognitive.db`

- This is the default memory database.
- It stores episodes, calibration history, and strategy playbooks.
- It is the main stateful learning surface for the subsystem.

### On backtest artifacts

`runner.py` writes the canonical artifact tree consumed by other repo surfaces:

- `backtest_results/cognitive/daily/<date>/summary.json`
- `backtest_results/cognitive/daily/<date>/planner_output.json`
- `backtest_results/cognitive/daily/<date>/analysis/<ticker>/*.json`
- `backtest_results/cognitive/daily/<date>/trades/<ticker>.json`
- `backtest_results/cognitive/daily/<date>/risk/risk_report.json`
- `backtest_results/cognitive/daily/<date>/normalized/workflow_artifact.json`
- `backtest_results/cognitive/daily/<date>/daily_report.md`
- `backtest_results/cognitive/ledgers/<date>.json`
- `backtest_results/cognitive/state/portfolio.json`
- `backtest_results/cognitive/state/recent_analysis_memory.json`
- `backtest_results/cognitive/state/strategy_memory_snapshot.json`
- `backtest_results/cognitive/state/calibration_summary.json`
- `backtest_results/cognitive/state/episodic_memory_summary.json`
- `backtest_results/cognitive/state/benchmark_metrics.json`
- `backtest_results/cognitive/playbooks/active_summary.json`
- `backtest_results/cognitive/state_snapshots/<date>.json`
- `backtest_results/cognitive/equity_curve.json`

### On backend/UI layers

- `cognitive_trading` is not a backend API server.
- The backend and dashboard are downstream consumers of its artifacts, not the runtime host.
- The dashboard reads the `backtest_results/cognitive/` tree for leaderboard, portfolio playback, trading view, and report pages.
- The backend runtime keeps `tracking_news` isolated from `cognitive_trading`; there is no direct backend API dependency on this package in the normal request path.

## 6. Framework / orchestration code vs concrete strategy logic

### Mostly orchestration / framework

- `runner.py`
- `planner/event_ledger.py`
- `planner/context_packer.py`
- `swarm/base_analyst.py`
- `decision/debate_engine.py`
- `decision/cio_agent.py`
- `memory/db.py`
- `memory/reflection_agent.py`
- `reporting/daily_reporter.py`
- `governance/schema_validator.py`
- `governance/confidence_calibrator.py`

### Mostly concrete strategy / policy logic

- `planner/planner_agent.py`
- `swarm/macro_analyst.py`
- `swarm/news_analyst.py`
- `swarm/technical_analyst.py`
- `swarm/quant_analyst.py`
- `swarm/financial_analyst.py`
- `decision/debate_trigger.py`
- `decision/risk_kernel.py`
- `memory/promotion_engine.py`
- `memory/episodic_store.py`
- `memory/calibration_store.py`
- `memory/strategy_store.py`

The boundary is not perfect, but that split is the useful one for reading the codebase.

## 7. File priority map

### Must-understand

- `cognitive_trading/config.py`
- `cognitive_trading/runner.py`
- `cognitive_trading/planner/event_ledger.py`
- `cognitive_trading/planner/context_packer.py`
- `cognitive_trading/planner/planner_agent.py`
- `cognitive_trading/swarm/base_analyst.py`
- `cognitive_trading/swarm/macro_analyst.py`
- `cognitive_trading/swarm/news_analyst.py`
- `cognitive_trading/swarm/technical_analyst.py`
- `cognitive_trading/swarm/quant_analyst.py`
- `cognitive_trading/swarm/financial_analyst.py`
- `cognitive_trading/governance/schemas.py`
- `cognitive_trading/governance/schema_validator.py`
- `cognitive_trading/governance/confidence_calibrator.py`
- `cognitive_trading/decision/debate_engine.py`
- `cognitive_trading/decision/cio_agent.py`
- `cognitive_trading/decision/risk_kernel.py`
- `cognitive_trading/memory/db.py`
- `cognitive_trading/memory/episodic_store.py`
- `cognitive_trading/memory/calibration_store.py`
- `cognitive_trading/memory/strategy_store.py`
- `cognitive_trading/memory/promotion_engine.py`
- `cognitive_trading/memory/reflection_agent.py`
- `cognitive_trading/reporting/daily_reporter.py`

### Read later

- `cognitive_trading/decision/debate_trigger.py`
- `cognitive_trading/governance/__init__.py`
- `cognitive_trading/memory/__init__.py`
- `cognitive_trading/decision/__init__.py`
- `cognitive_trading/reporting/__init__.py`
- `cognitive_trading/swarm/__init__.py`
- `cognitive_trading/__init__.py`

### Low priority

- `cognitive_trading/__init__.py`
- the package `__init__.py` files under the subpackages above

## 8. Exact next-file reading order

1. `cognitive_trading/config.py`
2. `cognitive_trading/runner.py`
3. `cognitive_trading/planner/event_ledger.py`
4. `cognitive_trading/planner/context_packer.py`
5. `cognitive_trading/planner/planner_agent.py`
6. `cognitive_trading/swarm/base_analyst.py`
7. `cognitive_trading/swarm/macro_analyst.py`
8. `cognitive_trading/swarm/news_analyst.py`
9. `cognitive_trading/swarm/technical_analyst.py`
10. `cognitive_trading/swarm/quant_analyst.py`
11. `cognitive_trading/swarm/financial_analyst.py`
12. `cognitive_trading/governance/schemas.py`
13. `cognitive_trading/governance/schema_validator.py`
14. `cognitive_trading/governance/confidence_calibrator.py`
15. `cognitive_trading/decision/debate_trigger.py`
16. `cognitive_trading/decision/debate_engine.py`
17. `cognitive_trading/decision/cio_agent.py`
18. `cognitive_trading/decision/risk_kernel.py`
19. `cognitive_trading/memory/db.py`
20. `cognitive_trading/memory/episodic_store.py`
21. `cognitive_trading/memory/calibration_store.py`
22. `cognitive_trading/memory/strategy_store.py`
23. `cognitive_trading/memory/promotion_engine.py`
24. `cognitive_trading/memory/reflection_agent.py`
25. `cognitive_trading/reporting/daily_reporter.py`

