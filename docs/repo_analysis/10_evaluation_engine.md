# evaluation_engine

The `evaluation_engine/` folder is not present in this workspace checkout, so I could not inspect its implementation directly.

## What I can confirm from the rest of the repo

- The dashboard expects evaluation artifacts under:
  - `../evaluation_engine/outputs/workflow_metrics/workflow_comparison.json`
- `dashboard/src/lib/summary-loader.cjs` reads that file when present and uses it to override summary metrics.
- The cognitive trading runner writes its own backtest artifacts under `backtest_results/cognitive/`, which are separate from the evaluation-engine output contract.

## Requested analysis status

Because the folder itself is missing from the working tree, I cannot reliably identify:

- entry files
- evaluators or metrics modules
- dataset/report generators
- judge or LLM-as-judge components
- internal file priority
- an exact next-file reading order

If the folder exists in another branch or submodule, I can analyze it once those files are available in the workspace.

