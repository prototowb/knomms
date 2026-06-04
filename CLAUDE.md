<!-- proto-gear:agent-context begin -->
<!-- proto-gear | role: agent-context | regenerate: pg sync-context -->

# Agent Context — knomms

> Auto-generated index every agent should read on session start.
> Regenerate with `pg sync-context`. **Do not hand-edit** between the BEGIN/END markers — your changes will be overwritten.

## 📋 Reference Index

| File | Purpose | Read When |
|------|---------|-----------|
| `AGENTS.md` | Agent orchestration, roles, pre-flight checklist | First session or unclear on process |
| `PROJECT_STATUS.md` | Current sprint, active tickets, project state | Every session before starting work |
| `PROJECT_SPECIFICATIONS.md` | Project planning doc — source for architecture | Starting features or design work (if exists) |
| `PROJECT_ARCHITECTURE.md` *(not present)* | Project-specific architecture (agent-extracted) | Design decisions (if exists) |
| `BRANCHING.md` | Git workflow, branch naming, commit format | Before any git operations |
| `TESTING.md` | TDD patterns, test pyramid, coverage targets | When writing tests |
| `.proto-gear/INDEX.md` | Capability catalog (full reference) | When the skim below is insufficient |

## 🛠 Available Capabilities

### **Skills** — apply to any task

- `skills/code-review` — Systematic code review methodology for maintaining code quality and knowledge sharing · _triggers:_ code review, pull request, pr review, review code
- `skills/debugging` — Systematic debugging methodology for identifying and fixing software issues · _triggers:_ debug, troubleshoot, bug, error
- `skills/documentation` — Writing clear, maintainable technical documentation for code and projects · _triggers:_ documentation, docs, readme, write docs
- `skills/performance` — Systematic performance optimization and profiling techniques · _triggers:_ performance, optimize, slow, profiling
- `skills/refactoring` — Systematic code refactoring techniques for improving code quality without changing behavior · _triggers:_ refactor, clean up, improve code, code smell
- `skills/security` — Security best practices and vulnerability prevention techniques · _triggers:_ security, vulnerability, authentication, authorization
- `skills/testing` — TDD methodology with red-green-refactor cycle for quality code · _triggers:_ write tests, testing, test coverage, tdd

### **Workflows** — multi-step processes

- `workflows/bug-fix` — Systematic workflow for investigating and fixing software defects · _triggers:_ bug, defect, error, issue
- `workflows/cicd-setup` — Setting up continuous integration and deployment pipelines · _triggers:_ ci cd, continuous integration, pipeline, automation
- `workflows/code-review-process` — Complete PR creation, review, approval, and merge workflow · _triggers:_ code review, pull request, PR, merge
- `workflows/complete-release` — End-to-end release workflow combining all release phases · _triggers:_ complete release, full release cycle, end-to-end release
- `workflows/dependency-update` — Systematic workflow for updating project dependencies safely · _triggers:_ update dependencies, upgrade packages, dependency maintenance, security updates
- `workflows/documentation-update` — Systematic workflow for maintaining and updating project documentation · _triggers:_ update docs, documentation, improve docs, docs maintenance
- `workflows/feature-development` — Complete workflow for developing new features from planning to deployment · _triggers:_ new feature, implement feature, build feature, add functionality
- `workflows/finalize-release` — Final steps for completing and announcing a release · _triggers:_ finalize release, post-release, announce release
- `workflows/hotfix` — Emergency workflow for critical production issues requiring immediate fixes · _triggers:_ hotfix, emergency, production issue, critical bug
- `workflows/incident-response` — Production issue handling from detection through resolution and post-mortem · _triggers:_ incident, outage, production down, alert
- `workflows/migration` — Breaking change and data migration workflow with rollback planning · _triggers:_ migration, breaking change, schema change, data migration
- `workflows/monitoring-setup` — Setting up monitoring, logging, and alerting for production systems · _triggers:_ monitoring, logging, alerting, observability
- `workflows/release` — Complete release process from preparation to deployment · _triggers:_ release, deploy, version, publish

### **Commands** — slash-command-style actions

- `commands/analyze-coverage` — Run and analyze test coverage for the project · _triggers:_ /analyze-coverage, coverage, test coverage, analyze coverage
- `commands/create-ticket` — Create and properly document a ticket in PROJECT_STATUS.md · _triggers:_ /create-ticket, create ticket, new ticket, add ticket
- `commands/generate-changelog` — Generate or update CHANGELOG.md from git history · _triggers:_ /generate-changelog, changelog, generate changelog, update changelog
- `commands/update-status` — Update ticket status in PROJECT_STATUS.md · _triggers:_ /update-status, /us, update status, change status

## 🔑 Trigger → Capability

When the user's prose contains these keywords, load the matching capability before responding.

| If user says... | Load |
|-----------------|------|
| `/analyze-coverage`, `coverage`, `test coverage`, `analyze coverage` | `commands/analyze-coverage` |
| `/create-ticket`, `create ticket`, `new ticket`, `add ticket` | `commands/create-ticket` |
| `/generate-changelog`, `changelog`, `generate changelog`, `update changelog` | `commands/generate-changelog` |
| `/update-status`, `/us`, `update status`, `change status`, `mark complete`, `mark completed` | `commands/update-status` |
| `code review`, `pull request`, `pr review`, `review code`, `feedback`, `quality check` | `skills/code-review` |
| `debug`, `troubleshoot`, `bug`, `error`, `issue`, `failing` | `skills/debugging` |
| `documentation`, `docs`, `readme`, `write docs`, `document code`, `api documentation` | `skills/documentation` |
| `performance`, `optimize`, `slow`, `profiling`, `benchmark`, `scalability` | `skills/performance` |
| `refactor`, `clean up`, `improve code`, `code smell`, `technical debt`, `restructure` | `skills/refactoring` |
| `security`, `vulnerability`, `authentication`, `authorization`, `encryption`, `owasp` | `skills/security` |
| `write tests`, `testing`, `test coverage`, `tdd`, `quality assurance`, `unit test` | `skills/testing` |
| `bug`, `defect`, `error`, `issue`, `broken`, `not working` | `workflows/bug-fix` |
| `ci cd`, `continuous integration`, `pipeline`, `automation`, `github actions`, `jenkins` | `workflows/cicd-setup` |
| `code review`, `pull request`, `PR`, `merge`, `review`, `approve` | `workflows/code-review-process` |
| `complete release`, `full release cycle`, `end-to-end release` | `workflows/complete-release` |
| `update dependencies`, `upgrade packages`, `dependency maintenance`, `security updates` | `workflows/dependency-update` |
| `update docs`, `documentation`, `improve docs`, `docs maintenance` | `workflows/documentation-update` |
| `new feature`, `implement feature`, `build feature`, `add functionality`, `feature request` | `workflows/feature-development` |
| `finalize release`, `post-release`, `announce release` | `workflows/finalize-release` |
| `hotfix`, `emergency`, `production issue`, `critical bug`, `urgent fix` | `workflows/hotfix` |
| `incident`, `outage`, `production down`, `alert`, `emergency`, `page` | `workflows/incident-response` |
| `migration`, `breaking change`, `schema change`, `data migration`, `backwards compatibility`, `major version` | `workflows/migration` |
| `monitoring`, `logging`, `alerting`, `observability`, `metrics` | `workflows/monitoring-setup` |
| `release`, `deploy`, `version`, `publish` | `workflows/release` |

## 🚨 Critical Rules

- NEVER push directly to `main` — always via PR from `development`; committing and pushing directly to `development` is allowed
- Run `pg status` before starting work to see active tickets and current sprint
- Use `pg ticket create "title" --type feature` to register new work
- Use `pg ticket update ID --status IN_PROGRESS` when starting a ticket

## 🤖 CLI Commands

- `pg status` — Current project state — version, sprint, active tickets
- `pg context [--regenerate]` — Print this Agent Context to stdout (pipe-friendly)
- `pg suggest "<task prose>" [--json]` — Match a free-form task description to the best-fitting capabilities
- `pg ticket create/update/list` — Manage tickets in PROJECT_STATUS.md
- `pg capabilities list [--type ...] [--json]` — Browse capabilities (--json for agent consumption)
- `pg capabilities show <name>` — Show full details of a capability
- `pg capabilities tree <name>` — Show dependency tree of a capability
- `pg agent list` — List configured custom agents (if any)
- `pg sync-context` — Regenerate Agent Context in all host files
- `pg sync-indexes` — Regenerate .proto-gear/INDEX.md and per-type INDEX.md from metadata.yaml
- `pg doctor [--fix] [--json]` — Audit project for proto-gear sync drift (use --fix to repair)
- `pg help` — Full CLI help

## 🌐 Project

- **Project**: knomms
- **Tech / type**: Self-hosted web application
- **Proto Gear version**: n/a
- **Last release**: n/a
- **Capabilities installed**: 7 skills, 13 workflows, 4 commands
- **Generated**: 2026-06-01 19:05

<!-- proto-gear:agent-context end -->
