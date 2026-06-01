# /create-ticket

> Creates a properly documented ticket in PROJECT_STATUS.md

## Invocation Syntax

```
/create-ticket "title" [--type TYPE] [--assignee NAME] [--priority LEVEL]
```

## Arguments

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `title` | Yes | string | - | Ticket title (must be in quotes) |
| `--type` | No | enum | task | One of: `feature`, `bugfix`, `hotfix`, `task` |
| `--assignee` | No | string | Unassigned | Agent or person responsible |
| `--priority` | No | enum | medium | One of: `low`, `medium`, `high`, `critical` |

## Examples

```
/create-ticket "Add user authentication"
/create-ticket "Fix memory leak in worker" --type bugfix --priority high
/create-ticket "Implement dark mode" --type feature --assignee "Frontend Agent"
/create-ticket "Update API docs" --type task --assignee "Documentation Agent"
```

---

## AI Execution Steps

> **For AI Agents**: Execute these steps exactly when `/create-ticket` is invoked.

### Step 1: Parse Arguments

Extract from user input:
- **title**: Text inside quotes (required)
- **--type**: Value after flag, default "task"
- **--assignee**: Value after flag, default "Unassigned"
- **--priority**: Value after flag, default "medium"

**If title missing**: Return error (see Error Handling below)

### Step 2: Read PROJECT_STATUS.md

Read `PROJECT_STATUS.md` from project root. Find in YAML metadata section:

```yaml
last_ticket_id: 42
ticket_prefix: "PROJ"
```

**If file not found**: Return error (see Error Handling below)

### Step 3: Calculate Ticket ID

```
next_id = last_ticket_id + 1
ticket_id = "{ticket_prefix}-{next_id:03d}"
```

Example: If `last_ticket_id: 42` and `ticket_prefix: "PROJ"`, next ticket is `PROJ-043`

### Step 4: Determine Branch Name (for reference)

Based on type, the future branch will be:
- feature: `feature/{ticket_id}-{slug}`
- bugfix: `bugfix/{ticket_id}-{slug}`
- hotfix: `hotfix/{ticket_id}-{slug}`
- task: `task/{ticket_id}-{slug}`

Where `slug` = lowercase title, spaces → hyphens, max 30 chars.

### Step 5: Update PROJECT_STATUS.md

**5a.** Add row to "Active Tickets" table:

```markdown
| {ticket_id} | {title} | {type} | PENDING | - | {assignee} |
```

**5b.** Update metadata:

```yaml
last_ticket_id: {next_id}
```

### Step 6: Confirm to User

Output confirmation:

```
Created ticket {ticket_id}: "{title}"
Type: {type} | Priority: {priority} | Status: PENDING
Assignee: {assignee}
Branch (when started): {branch_pattern}
```

---

## Completion Criteria

Command is complete when:
- [ ] Arguments parsed correctly
- [ ] Ticket ID is unique and sequential
- [ ] Ticket added to Active Tickets table in PROJECT_STATUS.md
- [ ] `last_ticket_id` incremented in metadata
- [ ] User received confirmation message

---

## Error Handling

| Condition | Error Message |
|-----------|---------------|
| No title provided | "Error: Missing required argument 'title'. Usage: `/create-ticket \"title\"`" |
| PROJECT_STATUS.md not found | "Error: PROJECT_STATUS.md not found. Initialize with `pg init` first." |
| Invalid --type value | "Error: Invalid type '{value}'. Must be one of: feature, bugfix, hotfix, task" |
| Invalid --priority value | "Error: Invalid priority '{value}'. Must be one of: low, medium, high, critical" |
| Malformed PROJECT_STATUS.md | "Error: Could not parse PROJECT_STATUS.md metadata. Check file format." |

---

## Complete Example

### User Input
```
/create-ticket "Add user authentication" --type feature --assignee "Backend Agent"
```

### Before (PROJECT_STATUS.md)

```markdown
# PROJECT STATUS

## Current State

```yaml
last_ticket_id: 42
ticket_prefix: "PROJ"
```

## Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-041 | Fix homepage load time | bugfix | IN_PROGRESS | bugfix/PROJ-041-fix-homepage | Performance Agent |
```

### After (PROJECT_STATUS.md)

```markdown
# PROJECT STATUS

## Current State

```yaml
last_ticket_id: 43
ticket_prefix: "PROJ"
```

## Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-041 | Fix homepage load time | bugfix | IN_PROGRESS | bugfix/PROJ-041-fix-homepage | Performance Agent |
| PROJ-043 | Add user authentication | feature | PENDING | - | Backend Agent |
```

### AI Output
```
Created ticket PROJ-043: "Add user authentication"
Type: feature | Priority: medium | Status: PENDING
Assignee: Backend Agent
Branch (when started): feature/PROJ-043-add-user-authentication
```

---

## Ticket Types Reference

| Type | Use Case | Branch Prefix |
|------|----------|---------------|
| **feature** | New functionality | `feature/` |
| **bugfix** | Fixing defects | `bugfix/` |
| **hotfix** | Emergency production fix | `hotfix/` |
| **task** | Non-feature work (refactor, docs, etc.) | `task/` |

## Ticket Status Workflow

```
PENDING → IN_PROGRESS → COMPLETED
   ↓           ↓
BLOCKED ←──────┘
   ↓
CANCELLED
```

## Ticket Naming Conventions

**Good titles** (verb + object):
- "Add user authentication"
- "Fix memory leak in image processor"
- "Refactor database connection pooling"

**Poor titles** (avoid):
- "Auth stuff" (vague)
- "Bug" (not descriptive)
- "URGENT!!!" (not descriptive)

---

## Related Commands

- `/update-status` - Change ticket status
- `/create-branch` - Create branch for ticket (if available)

## Related Workflows

- [Feature Development](../workflows/feature-development/WORKFLOW.md) - Uses `/create-ticket` in Step 1
- [Bug Fix](../workflows/bug-fix/WORKFLOW.md) - Uses `/create-ticket` to document bug

---

*Proto Gear `/create-ticket` Command v1.1 - Stable*
