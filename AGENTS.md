# Project Context

- Owner: Sreeharsha Kannegundla
- Default branch: main
- GitHub: https://github.com/Creator101-commits

---

# gstack — AI Engineering Workflow

gstack is a collection of SKILL.md files that give AI agents structured roles for
software development. Each skill is a specialist: CEO reviewer, eng manager,
designer, QA lead, release engineer, debugger, and more.

## Available skills

Skills live in `.agents/skills/` (or `~/.claude/skills/gstack/` on Claude Code).
Invoke them by name (e.g., `/office-hours`).

### Plan-mode reviews

| Skill | What it does |
|-------|-------------|
| `/office-hours` | Reframe product idea. |
| `/plan-ceo-review` | Find the 10-star product. |
| `/plan-eng-review` | Lock architecture & tests. |
| `/plan-design-review` | Rate design 0-10. |
| `/plan-devex-review` | DX audit (TTHW, friction). |
| `/plan-tune` | Tune question sensitivity. |
| `/autoplan` | CEO → design → eng → DX. |
| `/design-consultation` | Build design system. |
| `/spec` | Vague intent → spec. Files issue, spawns agent. |

### Implementation + review

| Skill | What it does |
|-------|-------------|
| `/review` | Pre-landing PR review. |
| `/codex` | OpenAI Codex second opinion. |
| `/investigate` | Root-cause debugging. |
| `/design-review` | Live-site visual audit. |
| `/design-shotgun` | Generate design variants. |
| `/design-html` | Production HTML/CSS. |
| `/devex-review` | Developer experience audit. |
| `/qa` | Browser QA + fix loop. |
| `/qa-only` | QA report only. |
| `/scrape` | Pull web page data. |
| `/skillify` | Codify scrape flow. |

### Release + deploy

| Skill | What it does |
|-------|-------------|
| `/ship` | Test → review → PR. |
| `/land-and-deploy` | Merge, deploy, verify. |
| `/canary` | Post-deploy monitoring. |
| `/landing-report` | Ship queue dashboard. |
| `/document-release` | Update docs. |
| `/document-generate` | Generate Diataxis docs. |
| `/setup-deploy` | Detect deploy config. |
| `/gstack-upgrade` | Update gstack. |

### Operational + memory

| Skill | What it does |
|-------|-------------|
| `/context-save` | Save context snapshot. |
| `/context-restore` | Resume saved context. |
| `/learn` | Manage learned data. |
| `/retro` | Weekly retro + streaks. |
| `/health` | Code quality dashboard. |
| `/benchmark` | Performance regression detection. |
| `/benchmark-models` | Cross-model benchmark. |
| `/cso` | OWASP + STRIDE audit. |
| `/setup-gbrain` | Set up gbrain sync. |
| `/sync-gbrain` | Sync gbrain with repo. |

### Browser + agent integration

| Skill | What it does |
|-------|-------------|
| `/browse` | Headless browser. |
| `/open-gstack-browser` | Visible browser + sidebar. |
| `/setup-browser-cookies` | Import browser cookies. |
| `/pair-agent` | Pair remote agent. |

### iOS QA — drive real iPhones over USB or Tailscale (v1.43.0.0+)

| Skill | What it does |
|-------|-------------|
| `/ios-qa` | Live-device QA via USB/Tailscale. |
| `/ios-fix` | Autonomous iOS bug fixer. |
| `/ios-design-review` | Apple HIG design audit. |
| `/ios-clean` | Strip debug wiring. |
| `/ios-sync` | Regenerate debug bridge. |

Companion CLIs (run on the Mac that's plugged into the device):

| Command | What it does |
|---------|-------------|
| `gstack-ios-qa-daemon` | Mac broker + Tailscale listener. |
| `gstack-ios-qa-mint` | Manage tailnet allowlist. |

End-to-end walkthrough: [docs/howto-ios-testing-with-gstack.md](docs/howto-ios-testing-with-gstack.md).

### Safety + scoping

| Skill | What it does |
|-------|-------------|
| `/careful` | Warn before destructive ops. |
| `/freeze` | Lock directory edits. |
| `/guard` | Careful + freeze. |
| `/unfreeze` | Remove edit restrictions. |
| `/make-pdf` | Markdown → PDF. |
| `/diagram` | Text → diagram (mermaid/SVG). |

## Build commands

```bash
bun install              # install dependencies
bun test                 # run free tests (no API spend)
bun run test:windows     # curated Windows-safe subset (runs on windows-latest)
bun run build            # generate docs + compile binaries
bun run gen:skill-docs   # regenerate SKILL.md files from templates
bun run skill:check      # health dashboard for all skills
```

## Platform support

- **macOS** + **Linux**: full test suite supported.
- **Windows**: curated Windows-safe subset runs on `windows-latest` via the
  `windows-free-tests` CI job. Setup script (`./setup`) requires Git Bash or
  MSYS today; native PowerShell support is a future expansion. The `bin/gstack-paths`
  helper resolves state roots through `CLAUDE_PLUGIN_DATA` / `GSTACK_HOME` so plugin
  installs work on every platform.

## Key conventions

- SKILL.md files are **generated** from `.tmpl` templates. Edit the template, not the output.
- Run `bun run gen:skill-docs --host codex` to regenerate Codex-specific output.
- The browse binary provides headless browser access. Use `$B <command>` in skills.
- Safety skills (careful, freeze, guard) use inline advisory prose — always confirm before destructive operations.
- State paths resolve via `bin/gstack-paths` (sourced via `eval "$(...)"`). Honors `GSTACK_HOME`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PLANS_DIR`.
- The `claude` CLI binary resolves via `browse/src/claude-bin.ts` (`Bun.which()` + `GSTACK_CLAUDE_BIN` override). Set `GSTACK_CLAUDE_BIN=wsl` plus `GSTACK_CLAUDE_BIN_ARGS='["claude"]'` to run Claude through WSL on Windows.

---

## Additional instructions for AI coding agents

Everything above this line is the project README, preserved as-is. The
instructions below are agent-specific and apply on top of it — read both.

### Definition of done

Before considering any task complete:

```bash
bun test              # must pass, no exceptions — it's free
bun run skill:check   # required if any SKILL.md, .tmpl, or skills/ file changed
```

Run `bun run test:windows` additionally when a change touches `bin/gstack-paths`,
`GSTACK_HOME`, `CLAUDE_PLUGIN_DATA`, `CLAUDE_PLANS_DIR`, or anything else on a
platform-path resolution route.

### Hard rules — do not violate these

- **Never hand-edit a generated `SKILL.md`.** These are compiled from `.tmpl`
  files via `bun run gen:skill-docs`. If a task needs different skill behavior
  or wording, edit the `.tmpl` source and regenerate. A direct edit to the
  output file will be silently overwritten on the next generation pass and the
  change will look like it "disappeared."
- **Don't bypass `bin/gstack-paths` for state/config paths.** Hardcoding a path
  that skips this resolution will break on at least one of `GSTACK_HOME`,
  `CLAUDE_PLUGIN_DATA`, or `CLAUDE_PLANS_DIR` setups.
- **Don't weaken `careful` / `freeze` / `guard` semantics.** `careful` and
  `guard` are advisory (confirm before destructive ops); `freeze` is a hard
  block on directory edits. Keep that distinction — don't quietly turn a hard
  block into advisory prose or vice versa while "simplifying" a skill.
- **Don't fabricate data** for `/benchmark`, `/benchmark-models`, Hackatime-style
  logs, or any other skill whose output is used for real measurement or
  competition tracking.
- **Don't install new dependencies without asking first**, and don't add a
  package manager other than Bun (no npm/yarn/pnpm lockfiles).

### Workflow expectations

- Prefer the existing skill over ad-hoc scripting: use `/ship` for
  test → review → push → PR rather than reimplementing that flow inline, use
  `/investigate` before proposing a fix for a reported bug, use `/review` as a
  pre-landing pass.
- If a change affects documented behavior, run `/document-release` or update
  `README.md` / Diataxis docs manually so they don't drift from the code.
- Keep commits atomic and scoped to one logical change.

## Rules

- Never force push to main
- Always write tests before marking a task done
- Use conventional commits (`feat:`, `fix:`, `chore:`)
- Never commit secrets, API keys, or `.env` files — verify `.gitignore` covers them
- Don't merge PRs with failing CI; flag it instead
- Ask before any irreversible action (deleting files, dropping tables, etc.)
- Don't install new dependencies without asking first
- Don't rewrite git history on shared branches without explicit confirmation
- Ask rather than guess when a task is ambiguous or underspecified
- Explain *why* in commit messages and PR descriptions for non-trivial changes
- Don't mark tasks done if tests were skipped, mocked, or not actually run
- No emojis in commit messages, code, or comments
- Write comments in simple language explaining *why* — keep them brief and only when necessary
- No emojis in READMEs, commit messages, or other non-code content
- Provide clear, concise descriptions in commit messages and PR descriptions
- Keep README in sync with code changes; verify consistency before every push, follow template structure exactly
- Check the project for existing templates and follow them exactly
- Always write fast, clean, and efficient code — optimize for performance and reliability. No performance regressions, technical debt, or slop. Code must be well-tested and production-ready before merging.

### Kilo Code CLI specifics

This repo is being worked on with **Kilo Code CLI**. Kilo auto-discovers this
file at the project root — no extra config needed for it to be loaded, and it
applies to every session in this repo.

A few Kilo-specific things worth knowing:

- Kilo also honors `.kilo/` for project-level config. If `kilo.jsonc` (or
  `.kilo/kilo.jsonc`) exists, check its `permission` block before assuming an
  action (bash, edit, webfetch) will run without a prompt — rules are
  evaluated by pattern match with the **last matching rule winning**.
- Subdirectory `AGENTS.md` files are supported and loaded dynamically when
  Kilo's Read tool touches a file in that directory — they supplement, not
  replace, this root file. If gstack's monorepo-style layout (e.g. per-package
  dirs) needs different rules than the root, add a scoped `AGENTS.md` there
  instead of overloading this one.
- Kilo's memory bank feature is deprecated in favor of `AGENTS.md`. If you see
  `.kilocode/rules/memory-bank/` content anywhere in this repo, treat this
  file as the source of truth going forward and fold anything still relevant
  from memory-bank into this file rather than maintaining both.
- Reusable slash-command workflows for Kilo live in `.kilo/commands/*.md`,
  separate from this repo's own `gstack` skills — don't confuse the two. A
  gstack skill (`/ship`, `/review`, etc.) is invoked the same way but is
  defined under `.agents/skills/` per the "Available skills" section above.
