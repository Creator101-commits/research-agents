# Project Context

- Owner: Sreeharsha Kannegundla
- Default branch: main
- GitHub: https://github.com/Creator101-commits/research-agents

---

# research-agents — Dairy Farm Agent-Based Model

A zero-dependency Python agent-based model of a dairy farm. It simulates cows,
feed, disease, manure, energy, water, environment, markets, processing,
genetics, farm management, and optional land management. Runtime is Python 3.10+
using only the standard library; Bun wraps the test scripts via `package.json`.

## Build commands

```bash
bun install                                                      # install test wrapper deps (Bun)
bun test                                                         # run test suite (Bun wrapper)
python3 -m unittest discover -s tests -p 'test_*.py'             # run full Python suite
python3 -m dairy_abm run --scenario scenarios/baseline.json --output output/   # example simulation run
python3 -m dairy_abm validate-config                             # validate calibration registry
```

## Platform support

- Python 3.10+ with the standard library only; macOS and Linux fully supported.
- No Windows-specific build script exists — do not invent one without checking
  `package.json` and CI configuration first.

## Key conventions

- `dairy_abm/model.py` owns the scheduler. Preserve the established daily order:
  Market → Sensors → optional Land → Feed/Crop → policy dispatch → Disease →
  water delivery → Cow → Processor → Manure → Energy → water accounting →
  Environment → Farm Manager → Genetics intake.
- Agents exchange data through `SimulationContext` and `Packet` objects; avoid
  direct agent-to-agent calls when a packet or shared state is appropriate.
- Preserve packet metadata (source, name, date, period, quality, confidence,
  stream identity) and the weekly Sunday / month-end / December 31 hooks.
- The same seed must produce deterministic replay — use the context's seeded
  RNG, never global randomness.
- `configs/calibration.json` is the authoritative parameter registry. New
  coefficients must include `value`, `unit`, `valid_range`, `source`,
  `assumption`, and `description`. Use `dairy_abm.config.value()` for dotted
  lookups and `load_calibration()` for loading/validation.
- Preserve mass, energy, nutrient, water, and financial conservation
  relationships; the environment ledger's duplicate detection must not be
  double-counted.
- `dairy_abm/reports.py` defines the report contract — update implementation,
  tests, and docs together when adding/renaming report fields.
- `output/` is generated and Git-ignored; never use it as a source fixture.
- Do not claim scientific or financial validity because tests pass — tests
  establish software contracts; calibration and domain review establish
  scientific validity.

---

## Rules

**Never**
- Force-push to main, or rewrite shared git history without explicit confirmation
- Install a new dependency or a different package manager without asking first
- Fabricate data — benchmarks, logs, test results, anything used for real measurement or grading
- Commit secrets, API keys, or `.env` files — confirm `.gitignore` covers them before pushing
- Merge a PR with failing CI — flag it instead
- Mark a task done if tests were skipped, mocked, or not actually run
- Use emojis anywhere: code, comments, commits, READMEs, docs

**Always**
- Ask before anything irreversible (deleting files, dropping tables, force push) or genuinely ambiguous — don't guess
- Write tests before marking a task done; keep dataset/eval leakage controls intact
- Use conventional commits (`feat:`, `fix:`, `chore:`); explain *why* in commit/PR messages for non-trivial changes
- Keep README in sync with code changes; follow the existing template in this repo exactly
- Keep comments brief, in plain language, explaining *why* — only when the code doesn't already say it
- Optimize for correctness and performance; no shortcuts that become silent tech debt
- {{Project-specific hard rule, e.g. "never hand-edit generated files"}}

*(Keep this file lean — instructions that just restate what the linter/type-checker/tests already enforce are wasted tokens on every session. Add project-specific rules above; don't pad with generic advice.)*

---

## Pi agent notes

Skip this whole section if running under a different agent (OpenCode, Codex, etc.) — everything below is Pi-specific.

Use the precise tool for the job instead of falling back to raw bash/grep:

| Extension | Use it for |
|---|---|
| `pi-web-access` | Anything needing current info — docs, library APIs, external verification |
| `@ff-labs/pi-fff` | Fuzzy file/content search, instead of guessing with `find`/`ls` |
| `pi-lsp` | Go-to-def, references, diagnostics — precise, not grep-based |
| `pi-repos` | Reading/referencing another GitHub repo without cloning |
| `repo-baby` | Codebase orientation (symbol map, ranked read order) — unfamiliar or inherited repos only |
| `pi-hashline-edit-pro` | Default file-editing path, not raw find/replace |
| `pi-blackhole` | Deterministic compaction + observational memory (observations + reflections) that survives compaction. If a session went through compaction, use `recall`/`/blackhole-recall <query>` to pull exact detail — file paths, errors, prior decisions — rather than assuming it's gone. `/blackhole-memory status` shows pipeline state. |
| `pi-skill-optimizer` | Passive — no action needed |
| `@juicesharp/rpiv-ask-user-question` | Structured clarifying question instead of guessing |
| `@juicesharp/rpiv-todo` | Track state on any task with 3+ discrete steps |
| `@narumitw/pi-plan-mode` | Plan before implementing anything non-trivial or architecturally significant |
| `@vanillagreen/pi-session-manager` | Check for a resumable session before assuming a fresh start |
| `pi-simplify` | Run `/simplify` on changed lines before calling non-trivial work done |
| `@dietrichgebert/ponytail` | YAGNI by default — reuse, fix root causes, not call-site patches. Shortcuts need a ponytail comment with a named ceiling. {{Note here if this repo is research/scientific code where "minimum code" is the wrong default.}} |
| `pi-frontend-create` | Auto-activates on UI/web/app work. Banned-pattern list + 13-point anti-pattern checklist. Run `/simplify` after. |
