# 00 — Baseline Validation Results

Date: 2026-07-09
Branch: master (clean working tree at audit start)
Runner: local Windows, `venv/` Python 3.12.2

All baseline checks were run BEFORE any audit modification, so any later failure
can be attributed to audit work rather than a pre-existing condition.

## Detected toolchain / commands

| Purpose | Command | Source |
|---------|---------|--------|
| Backend unit/integration tests | `pytest tests/ -q` | CLAUDE.md, `.github/workflows/ci.yml` |
| Lint | `ruff check api rag ingestion config.py` | `pyproject.toml`, CI |
| Type-check (advisory) | `mypy` (files=`config.py` only) | `pyproject.toml`, CI |
| Dependency audit (advisory) | `pip-audit` | CI |
| Frontend tests | `npm test` → `vitest run` | `frontend/package.json` |
| Frontend build | `npm run build` → `vite build` | `frontend/package.json` |
| Backend server | `uvicorn api.main:app` | `Dockerfile`, `api/main.py` |

Python invoked via `.\venv\Scripts\python.exe`. Tests were run with CI's dummy
env (`GEMINI_API_KEY=test PINECONE_API_KEY=test RELIEFWEB_APPNAME=test`) to avoid
any accidental live upstream call. The suite is fully mocked/offline.

## Results (all green)

| Check | Command | Result |
|-------|---------|--------|
| Backend tests | `pytest tests/ -q` | **488 passed** in 11.94s |
| Lint | `ruff check api rag ingestion config.py` | All checks passed (exit 0) |
| Type-check | `mypy` | Success: no issues found in 1 source file (exit 0) |
| Frontend tests | `vitest run` | **81 passed** (11 files), exit 0 |
| Frontend build | `vite build` | built in 3.12s, exit 0 |

## Not yet run (deferred; require network / live advisory data)

- `pip-audit` — needs live PyPI advisory DB. MEMORY.md records a prior run:
  advisory `18 CVE / 9 packages`, `continue-on-error` in CI so it never blocks.
  To be re-checked in PASS 15 with the exact `package@version` list; treated as
  NEEDS-CONTEXT until a fresh run is captured.
- `npm audit` (frontend) — deferred to PASS 15.

## Notes

- `mypy` is intentionally scoped to `config.py` only (`files = ["config.py"]` in
  `pyproject.toml`); the rest of the codebase is untyped by design. This is a
  known, deliberate limitation — NOT an audit finding, but it means type-checking
  provides near-zero coverage as a correctness signal for `api/`, `rag/`,
  `ingestion/`.
- `ruff` rule set is `E4/E7/E9 + F` (pyflakes + a pycodestyle subset) — catches
  unused imports / undefined names, not style. No security linter (e.g. `bandit`)
  is configured; noted for PASS 15/16.
