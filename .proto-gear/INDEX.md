# Proto Gear Capabilities Index

> **For AI Agents**: This is the master catalog of available capabilities.
> Read this file to discover slash commands, skills, and workflows.

## Quick Navigation

- [Slash Commands](#slash-commands) - **Explicit invocation** via `/command-name`
- [Skills](#skills) - Implicit expertise (always active when relevant)
- [Workflows](#workflows) - Multi-step processes
- [Agents](#agents) - Specialized agent patterns

---

<!-- proto-gear:capability-index begin -->

## Capability Summary

_Auto-generated from `metadata.yaml`. Hand-edits inside this block are overwritten by `pg sync-indexes`._

### Skills (7)

| ID | Name | Description | Triggers |
|----|------|-------------|----------|
| `skills/code-review` | Code Review Best Practices | Systematic code review methodology for maintaining code quality and knowledge sharing | `code review`, `pull request`, `pr review`, `review code` |
| `skills/debugging` | Debugging & Troubleshooting | Systematic debugging methodology for identifying and fixing software issues | `debug`, `troubleshoot`, `bug`, `error` |
| `skills/documentation` | Technical Documentation | Writing clear, maintainable technical documentation for code and projects | `documentation`, `docs`, `readme`, `write docs` |
| `skills/performance` | Performance Optimization | Systematic performance optimization and profiling techniques | `performance`, `optimize`, `slow`, `profiling` |
| `skills/refactoring` | Code Refactoring | Systematic code refactoring techniques for improving code quality without changing behavior | `refactor`, `clean up`, `improve code`, `code smell` |
| `skills/security` | Security Best Practices | Security best practices and vulnerability prevention techniques | `security`, `vulnerability`, `authentication`, `authorization` |
| `skills/testing` | Test-Driven Development | TDD methodology with red-green-refactor cycle for quality code | `write tests`, `testing`, `test coverage`, `tdd` |

**Detail**: [skills/INDEX.md](skills/INDEX.md)

### Workflows (13)

| ID | Name | Description | Triggers |
|----|------|-------------|----------|
| `workflows/bug-fix` | Bug Fix Workflow | Systematic workflow for investigating and fixing software defects | `bug`, `defect`, `error`, `issue` |
| `workflows/cicd-setup` | CI/CD Setup Workflow | Setting up continuous integration and deployment pipelines | `ci cd`, `continuous integration`, `pipeline`, `automation` |
| `workflows/code-review-process` | Code Review Process Workflow | Complete PR creation, review, approval, and merge workflow | `code review`, `pull request`, `PR`, `merge` |
| `workflows/complete-release` | Complete Release Workflow | End-to-end release workflow combining all release phases | `complete release`, `full release cycle`, `end-to-end release` |
| `workflows/dependency-update` | Dependency Update Workflow | Systematic workflow for updating project dependencies safely | `update dependencies`, `upgrade packages`, `dependency maintenance`, `security updates` |
| `workflows/documentation-update` | Documentation Update Workflow | Systematic workflow for maintaining and updating project documentation | `update docs`, `documentation`, `improve docs`, `docs maintenance` |
| `workflows/feature-development` | Feature Development Workflow | Complete workflow for developing new features from planning to deployment | `new feature`, `implement feature`, `build feature`, `add functionality` |
| `workflows/finalize-release` | Finalize Release Workflow | Final steps for completing and announcing a release | `finalize release`, `post-release`, `announce release` |
| `workflows/hotfix` | Hotfix Workflow | Emergency workflow for critical production issues requiring immediate fixes | `hotfix`, `emergency`, `production issue`, `critical bug` |
| `workflows/incident-response` | Incident Response Workflow | Production issue handling from detection through resolution and post-mortem | `incident`, `outage`, `production down`, `alert` |
| `workflows/migration` | Migration Workflow | Breaking change and data migration workflow with rollback planning | `migration`, `breaking change`, `schema change`, `data migration` |
| `workflows/monitoring-setup` | Monitoring Setup Workflow | Setting up monitoring, logging, and alerting for production systems | `monitoring`, `logging`, `alerting`, `observability` |
| `workflows/release` | Release Workflow | Complete release process from preparation to deployment | `release`, `deploy`, `version`, `publish` |

**Detail**: [workflows/INDEX.md](workflows/INDEX.md)

### Slash Commands (4)

| ID | Name | Description | Triggers |
|----|------|-------------|----------|
| `commands/analyze-coverage` | Analyze Coverage | Run and analyze test coverage for the project | `/analyze-coverage`, `coverage`, `test coverage`, `analyze coverage` |
| `commands/create-ticket` | Create Ticket | Create and properly document a ticket in PROJECT_STATUS.md | `/create-ticket`, `create ticket`, `new ticket`, `add ticket` |
| `commands/generate-changelog` | Generate Changelog | Generate or update CHANGELOG.md from git history | `/generate-changelog`, `changelog`, `generate changelog`, `update changelog` |
| `commands/update-status` | Update Status | Update ticket status in PROJECT_STATUS.md | `/update-status`, `/us`, `update status`, `change status` |

**Detail**: [commands/INDEX.md](commands/INDEX.md)

### Agents (0)

_No agents installed._

<!-- proto-gear:capability-index end -->

---

## Slash Commands

> **Explicit invocation** - Human types `/command-name` to trigger

For the canonical list of shipped slash commands, see the **Capability Summary** above (auto-generated from `metadata.yaml`) or **[commands/INDEX.md](commands/INDEX.md)** for full per-command syntax tables.

### How to Recognize Slash Commands

When user input starts with `/`, it's a slash command. Slash commands are **explicit instructions** — different from natural language requests:

| Input Type | Example | AI Response |
|------------|---------|-------------|
| **Slash Command** | `/create-ticket "Add auth"` | Execute command exactly as documented |
| **Natural Language** | "create a ticket for auth" | AI decides how to accomplish |

### Slash Command Execution Protocol

When you recognize a slash command:

1. **Parse the input**:
   - Command name: word after `/` (e.g., `create-ticket`)
   - Required args: values in quotes (e.g., `"Add user authentication"`)
   - Optional flags: `--flag value` pairs

2. **Locate command documentation**:
   ```
   .proto-gear/commands/{command-name}/COMMAND.md
   ```

3. **Validate arguments**:
   - Check required arguments are present
   - Validate optional values against allowed values
   - Return error if validation fails

4. **Execute AI Execution Steps**:
   - Follow the numbered steps in the command's documentation exactly
   - Use native tools (Read, Edit, Bash) as described

5. **Confirm completion**:
   - Report the result as specified in the command

### Example Execution

```
User: /create-ticket "Add dark mode" --type feature

AI:
1. Parse: command=create-ticket, title="Add dark mode", --type=feature
2. Read: .proto-gear/commands/create-ticket/COMMAND.md
3. Validate: title present ✓, --type is valid enum ✓
4. Execute:
   - Read PROJECT_STATUS.md → last_ticket_id=42, prefix=PROJ
   - Calculate: PROJ-043
   - Edit PROJECT_STATUS.md: add ticket row, increment last_ticket_id
5. Confirm: "Created ticket PROJ-043: Add dark mode"
```

### Slash Command Autocomplete Protocol

> **For AI Agents**: Implement autocomplete when user types `/command...`

**When to Activate**: When user message starts with `/` or user is typing a partial command (e.g., `/cre`, `/ana`, `/gen`).

**Step 1: Match User Input**

When user types a partial command, filter commands where name starts with input:
- `/cre` → matches `/create-ticket`
- `/a` → matches `/analyze-coverage`

**Step 2: Suggest to User**

Present matching command(s) with:
- **Command name**: `/create-ticket`
- **Short description**: "Create ticket in PROJECT_STATUS.md"
- **Syntax hint**: `"title" [--type TYPE] [--assignee NAME]`

**Step 3: Argument Autocomplete**

When user types `/create-ticket "title" --`, suggest available flags:
- `--type` (feature, bugfix, hotfix, task)
- `--assignee` (agent or person name)
- `--priority` (low, medium, high, critical)

When user types `/create-ticket "title" --type `, suggest valid values:
- `feature`, `bugfix`, `hotfix`, `task`

### Command Shortcuts

For efficiency, memorize these shortcuts:

| Shortcut | Full Command | Purpose |
|----------|--------------|---------|
| `/ct` | `/create-ticket` | Create ticket |
| `/ac` | `/analyze-coverage` | Coverage analysis |
| `/gc` | `/generate-changelog` | Generate changelog |

### Implementation Notes for AI Agents

1. **Cache the command list**: After first read, remember available commands for the session
2. **Prefix matching**: Match from start of command name (case-insensitive)
3. **Show shortcuts**: When suggesting, show both full name and shortcut
4. **Validate early**: Check arguments before executing
5. **Clear feedback**: Show what command will do before executing

---

## Skills

> **Implicit activation** - AI applies when contextually relevant (no `/` prefix)

Modular, reusable expertise in specific domains. See the **Capability Summary** above for the full skills list (auto-generated from `metadata.yaml`), or **[skills/INDEX.md](skills/INDEX.md)** for each skill's triggers, contexts, and dependencies.

**Note**: Skills are NOT invoked with `/`. They're expertise you apply based on context.

---

## Workflows

> **Multi-step processes** - May use slash commands as building blocks

Workflows orchestrate multiple commands and skills together. See the **Capability Summary** above for the full workflow list, or **[workflows/INDEX.md](workflows/INDEX.md)** for steps, durations, and dependencies per workflow.

---

## Agents

Specialized agent patterns:

*No specialized agents included in this configuration.*

To add specialized agent patterns, re-run `pg init` with the `--with-agents` option.

---

## Slash Commands vs Skills vs Workflows

| Type | Invocation | Nature | Example |
|------|------------|--------|---------|
| **Slash Command** | `/command-name` (explicit) | Discrete action | `/create-ticket "Add auth"` |
| **Skill** | Automatic (implicit) | Continuous expertise | "testing" skill during TDD |
| **Workflow** | Context-based | Multi-step process | "feature-development" for new features |

**Key Insight**:
- **Commands** = Human says "do this specific thing now"
- **Skills** = Expertise AI applies throughout a task
- **Workflows** = Orchestrated sequences (may include commands)

---

## Discovery Workflow

**For AI Agents**: When starting a task:

1. **Check for slash commands** - Did user type `/something`? Execute it.
2. **Read this INDEX.md** - Discover available capabilities
3. **Match task to capabilities** - Find relevant skills/workflows
4. **Load relevant files** - Read the specific .md files
5. **Follow patterns** - Use native tools (git, pytest, npm, etc.)
6. **Update status** - Use `/create-ticket`, `/update-status` as needed

---

## Integration with Core Templates

This capability system **extends** Proto Gear's core templates:

- **AGENTS.md** - Core agent configuration, extended by `.proto-gear/agents/`
- **PROJECT_STATUS.md** - Updated by `/create-ticket`, `/update-status`
- **BRANCHING.md** - Git workflow conventions
- **TESTING.md** - TDD patterns, detailed in `skills/testing/`

---

## Adding Custom Capabilities

### Adding a Slash Command

1. Create `commands/your-command/COMMAND.md`
2. Include: Invocation Syntax, Arguments, AI Execution Steps, Error Handling
3. Update `commands/INDEX.md` to list it
4. Update this INDEX.md Quick Reference table

### Adding a Skill

1. Create `skills/your-skill/SKILL.md`
2. Skills are implicit - describe when to activate
3. Update `skills/INDEX.md` to list it

### Adding a Workflow

1. Create `workflows/your-workflow/WORKFLOW.md`
2. Reference commands and skills used
3. Update `workflows/INDEX.md` to list it

---

## Need More Capabilities?

This is a minimal set. For a complete capability library:

```bash
pg init --with-capabilities=full
```

Includes:
- Additional skills (debugging, code-review, security, performance)
- More workflows (bug-fix, hotfix, release)
- Additional commands (update-status, create-branch)
- Specialized agents (backend, frontend, testing, devops)

---

*Proto Gear Universal Capabilities System v1.1*
*Generated by Proto Gear 0.10.0*
