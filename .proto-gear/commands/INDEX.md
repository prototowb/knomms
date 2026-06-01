# Slash Commands Reference

> **For AI Agents**: When a human types `/command-name`, find the command here and execute it.

## Quick Reference

| Command | Shortcut | Syntax | Purpose |
|---------|----------|--------|---------|
| `/create-ticket` | `/ct` | `"title" [--type TYPE]` | Create ticket in PROJECT_STATUS.md |
| `/update-status` | `/us` | `<ID> <STATUS> [--reason]` | Update ticket status |
| `/analyze-coverage` | `/ac` | `[--path DIR]` | Analyze test coverage |
| `/generate-changelog` | `/gc` | `[--since VER]` | Generate CHANGELOG.md |

### Shortcuts

For faster invocation, use these shortcuts:

```
/ct  →  /create-ticket
/us  →  /update-status
/ac  →  /analyze-coverage
/gc  →  /generate-changelog
```

**Note**: Shortcuts expand to the full command. Arguments work the same way:
- `/ct "Add auth"` = `/create-ticket "Add auth"`
- `/us PROJ-043 COMPLETED` = `/update-status PROJ-043 COMPLETED`
- `/ac --path src/` = `/analyze-coverage --path src/`

---

<!-- proto-gear:capability-index begin -->

## Available Slash Commands (4)

_Auto-generated from `metadata.yaml`. Hand-edits inside this block are overwritten by `pg sync-indexes`._

### Analyze Coverage

- **ID**: `commands/analyze-coverage`
- **File**: `analyze-coverage/COMMAND.md`
- **Version**: 1.1.0
- **Status**: stable
- **Category**: testing
- **Description**: Run and analyze test coverage for the project
- **Tags**: coverage, testing, analysis, quality, metrics
- **Triggers**: "/analyze-coverage", "coverage", "test coverage", "analyze coverage"
- **Contexts**: When user types /analyze-coverage; After running tests; Before merging code; During code review
- **Dependencies**: optional: `skills/testing`; suggested: `workflows/feature-development`
- **Agent roles**: Testing Agent, Quality Assurance Agent, Full-Stack Developer Agent

### Create Ticket

- **ID**: `commands/create-ticket`
- **File**: `create-ticket/COMMAND.md`
- **Version**: 1.1.0
- **Status**: stable
- **Category**: project-management
- **Description**: Create and properly document a ticket in PROJECT_STATUS.md
- **Tags**: ticket, planning, status, documentation, sprint, tracking
- **Triggers**: "/create-ticket", "create ticket", "new ticket", "add ticket"
- **Contexts**: When user types /create-ticket; When starting any new work item; Before beginning features; After discovering bugs
- **Dependencies**: optional: `workflows/feature-development`, `workflows/bug-fix`
- **Agent roles**: Project Manager Agent, All Agents

### Generate Changelog

- **ID**: `commands/generate-changelog`
- **File**: `generate-changelog/COMMAND.md`
- **Version**: 1.1.0
- **Status**: stable
- **Category**: release-management
- **Description**: Generate or update CHANGELOG.md from git history
- **Tags**: changelog, release, documentation, versioning, history
- **Triggers**: "/generate-changelog", "changelog", "generate changelog", "update changelog"
- **Contexts**: When user types /generate-changelog; Before releases; After completing features; For version documentation
- **Dependencies**: optional: `workflows/release`, `workflows/finalize-release`; suggested: `skills/documentation`
- **Agent roles**: Release Manager Agent, Documentation Agent, DevOps Agent

### Update Status

- **ID**: `commands/update-status`
- **File**: `update-status/COMMAND.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: project-management
- **Description**: Update ticket status in PROJECT_STATUS.md
- **Tags**: ticket, status, workflow, tracking, sprint, progress
- **Triggers**: "/update-status", "/us", "update status", "change status", "mark complete", "mark completed", "start work", "ticket blocked"
- **Contexts**: When user types /update-status or /us; When starting work on a ticket; When completing a ticket; When blocked by dependency; During workflow step transitions
- **Dependencies**: optional: `commands/create-ticket`, `workflows/feature-development`, `workflows/bug-fix`
- **Agent roles**: Project Manager Agent, All Agents

<!-- proto-gear:capability-index end -->

---

## AI Execution Protocol

When you recognize a slash command (input starting with `/`):

### Step 1: Parse the Input

Extract:
- **Command name**: The word after `/` (e.g., `create-ticket`)
- **Required arguments**: Values in quotes or without flags
- **Optional flags**: `--flag value` pairs

**Example parsing**:
```
Input: /create-ticket "Add auth" --type feature --assignee "Backend Agent"

Command: create-ticket
Arguments:
  - title: "Add auth" (required)
  - --type: feature
  - --assignee: "Backend Agent"
```

### Step 2: Locate Command Documentation

Read the command file:
```
.proto-gear/commands/{command-name}/COMMAND.md
```

### Step 3: Validate Arguments

Check against the command's Arguments table:
- Are all required arguments present?
- Are optional values valid (e.g., --type must be feature|bugfix|hotfix|task)?

**If validation fails**: Return the error message from the command's Error Handling section.

### Step 4: Execute AI Execution Steps

Follow the numbered steps in the command's "AI Execution Steps" section exactly.

### Step 5: Confirm Completion

Report the result to the user as specified in the command's Step 6 (or equivalent).

---

## Slash Commands vs Skills

| Aspect | Slash Commands | Skills |
|--------|---------------|--------|
| **Invocation** | Explicit: Human types `/command` | Implicit: AI activates when relevant |
| **Syntax** | `/command-name "arg" --flag value` | No special syntax |
| **Nature** | Discrete, one-time action | Continuous expertise |
| **Duration** | Start → Finish → Done | Active throughout task |
| **Output** | Specific deliverable | Ongoing guidance |
| **Example** | `/create-ticket "Add login"` | "testing" skill active during TDD |

**Key Difference**:
- Slash commands are **explicit instructions** from the human
- Skills are **expertise you apply** based on context

---

## Error Handling

When a slash command fails, report clearly:

```
Error: {specific error message}
Usage: {correct syntax}
```

**Example**:
```
Error: Missing required argument 'title'
Usage: /create-ticket "title" [--type TYPE]
```

---

## Adding Custom Slash Commands

To add a new slash command:

1. **Create directory**: `commands/your-command/`
2. **Create COMMAND.md** with this structure:
   ```markdown
   ---
   name: "Your Command"
   type: "command"
   slash_command: "/your-command"
   arguments:
     required:
       - name: "arg1"
         type: "string"
     optional:
       - name: "--flag"
         type: "enum"
         values: ["a", "b", "c"]
         default: "a"
   ---

   # /your-command

   ## Invocation Syntax
   ## Arguments
   ## AI Execution Steps
   ## Completion Criteria
   ## Error Handling
   ```
3. **Update this INDEX.md** to list the new command

---

## Integration with Workflows

Slash commands are building blocks for workflows:

| Workflow | Uses Commands |
|----------|---------------|
| Feature Development | `/create-ticket` → `/update-status` → `/analyze-coverage` |
| Bug Fix | `/create-ticket` → `/update-status` → testing |
| Code Review Process | `/update-status` (after merge) |
| Release | `/generate-changelog` |
| Incident Response | `/create-ticket` (follow-ups) |
| Migration | `/create-ticket` → `/update-status` |

Workflows **orchestrate** multiple commands; commands are **atomic actions**.

---

*Proto Gear Slash Commands Reference v1.1*
