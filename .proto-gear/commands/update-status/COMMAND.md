# /update-status

> Updates ticket status in PROJECT_STATUS.md

**Shortcut**: `/us`

## Invocation Syntax

```
/update-status <TICKET_ID> <STATUS> [--reason REASON] [--branch BRANCH]
/us <TICKET_ID> <STATUS> [--reason REASON] [--branch BRANCH]
```

## Arguments

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `ticket_id` | Yes | string | - | Ticket ID (e.g., PROJ-043) |
| `status` | Yes | enum | - | One of: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED` |
| `--reason` | No* | string | - | Reason for change (*required when status is BLOCKED) |
| `--branch` | No | string | auto | Branch name (set when transitioning to IN_PROGRESS) |

## Examples

```
/update-status PROJ-043 IN_PROGRESS
/update-status PROJ-043 COMPLETED
/update-status PROJ-043 BLOCKED --reason "Waiting for API spec from backend team"
/update-status PROJ-043 IN_PROGRESS --branch feature/PROJ-043-add-auth
/us PROJ-043 COMPLETED
/us PROJ-044 IN_PROGRESS
```

---

## AI Execution Steps

> **For AI Agents**: Execute these steps exactly when `/update-status` or `/us` is invoked.

### Step 1: Parse Arguments

Extract from user input:
- **ticket_id**: Ticket identifier (e.g., PROJ-043) - required
- **status**: New status value - required
- **--reason**: Optional reason text
- **--branch**: Optional branch name

**Validation**:
- `ticket_id` must match pattern: `{PREFIX}-{NUMBER}` (e.g., PROJ-043, BUG-001)
- `status` must be one of: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `BLOCKED`
- If `status` is `BLOCKED`, `--reason` should be provided (warn if missing)

**If ticket_id missing**: Return error (see Error Handling below)
**If status missing or invalid**: Return error (see Error Handling below)

### Step 2: Read PROJECT_STATUS.md

Read `PROJECT_STATUS.md` from project root. Find the "Active Tickets" table:

```markdown
## Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-043 | Add user authentication | feature | PENDING | - | Backend Agent |
```

**If file not found**: Return error
**If ticket not found in table**: Return error

### Step 3: Validate Status Transition

Check that the status transition is valid:

```
Valid transitions:
  PENDING     -> IN_PROGRESS, BLOCKED
  IN_PROGRESS -> COMPLETED, BLOCKED
  BLOCKED     -> IN_PROGRESS
  COMPLETED   -> IN_PROGRESS (reopen - warn user)
```

| Current Status | Allowed Next Status |
|----------------|---------------------|
| PENDING | IN_PROGRESS, BLOCKED |
| IN_PROGRESS | COMPLETED, BLOCKED |
| BLOCKED | IN_PROGRESS |
| COMPLETED | IN_PROGRESS (with warning) |

**If invalid transition**: Return error with valid options

### Step 4: Prepare Updates

Based on new status, determine what to update:

**If transitioning to IN_PROGRESS**:
- If `--branch` provided: Use that branch name
- If no `--branch`: Auto-generate from ticket type and ID
  - Format: `{type}/{ticket_id}-{slug}`
  - Example: `feature/PROJ-043-add-user-auth`

**If transitioning to BLOCKED**:
- Capture `--reason` (warn if not provided)
- Branch column remains unchanged

**If transitioning to COMPLETED**:
- Branch column remains unchanged
- Consider moving ticket to Completed Tickets section (optional)

### Step 5: Update PROJECT_STATUS.md

Find the ticket row and update the Status column (and Branch if applicable):

**Before**:
```markdown
| PROJ-043 | Add user authentication | feature | PENDING | - | Backend Agent |
```

**After (IN_PROGRESS with branch)**:
```markdown
| PROJ-043 | Add user authentication | feature | IN_PROGRESS | feature/PROJ-043-add-user-auth | Backend Agent |
```

**After (BLOCKED with reason)**:
```markdown
| PROJ-043 | Add user authentication | feature | BLOCKED | - | Backend Agent |
```
Note: Reason can be added as a comment or in a separate notes section.

### Step 6: Confirm to User

Output confirmation:

```
Updated {ticket_id}: {old_status} -> {new_status}
Title: "{title}"
Branch: {branch}
```

**If BLOCKED**:
```
Updated {ticket_id}: {old_status} -> BLOCKED
Title: "{title}"
Reason: {reason}
```

**If reopening from COMPLETED**:
```
Warning: Reopening completed ticket.
Updated {ticket_id}: COMPLETED -> IN_PROGRESS
Title: "{title}"
Branch: {branch}
```

---

## Completion Criteria

Command is complete when:
- [ ] Arguments parsed correctly
- [ ] Ticket found in PROJECT_STATUS.md
- [ ] Status transition validated
- [ ] PROJECT_STATUS.md updated with new status
- [ ] Branch column updated (if applicable)
- [ ] User received confirmation message

---

## Error Handling

| Condition | Error Message |
|-----------|---------------|
| No ticket_id provided | "Error: Missing required argument 'ticket_id'. Usage: `/update-status PROJ-043 IN_PROGRESS`" |
| No status provided | "Error: Missing required argument 'status'. Usage: `/update-status PROJ-043 IN_PROGRESS`" |
| Invalid status value | "Error: Invalid status '{value}'. Must be one of: PENDING, IN_PROGRESS, COMPLETED, BLOCKED" |
| Ticket not found | "Error: Ticket '{ticket_id}' not found in PROJECT_STATUS.md Active Tickets table." |
| Invalid transition | "Error: Cannot transition from {current} to {new}. Valid next states: {valid_states}" |
| PROJECT_STATUS.md not found | "Error: PROJECT_STATUS.md not found. Initialize with `pg init` first." |
| BLOCKED without reason | "Warning: BLOCKED status should include --reason. Proceeding without reason." |

---

## Complete Example

### User Input
```
/update-status PROJ-043 IN_PROGRESS --branch feature/PROJ-043-add-user-auth
```

### Before (PROJECT_STATUS.md)

```markdown
## Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-042 | Fix homepage load time | bugfix | IN_PROGRESS | bugfix/PROJ-042-fix-homepage | Performance Agent |
| PROJ-043 | Add user authentication | feature | PENDING | - | Backend Agent |
```

### After (PROJECT_STATUS.md)

```markdown
## Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-042 | Fix homepage load time | bugfix | IN_PROGRESS | bugfix/PROJ-042-fix-homepage | Performance Agent |
| PROJ-043 | Add user authentication | feature | IN_PROGRESS | feature/PROJ-043-add-user-auth | Backend Agent |
```

### AI Output
```
Updated PROJ-043: PENDING -> IN_PROGRESS
Title: "Add user authentication"
Branch: feature/PROJ-043-add-user-auth
```

---

## Status Transition Diagram

```
                    +-----------+
                    |  PENDING  |
                    +-----+-----+
                          |
            +-------------+-------------+
            |                           |
            v                           v
    +-------+-------+           +-------+-------+
    |  IN_PROGRESS  |<--------->|    BLOCKED    |
    +-------+-------+           +---------------+
            |
            v
    +-------+-------+
    |   COMPLETED   |
    +---------------+
            |
            v (reopen with warning)
    +-------+-------+
    |  IN_PROGRESS  |
    +---------------+
```

## Status Meanings

| Status | Meaning | Typical Actions |
|--------|---------|-----------------|
| **PENDING** | Work not yet started | Waiting in backlog, needs assignment |
| **IN_PROGRESS** | Actively being worked on | Developer working, commits happening |
| **BLOCKED** | Cannot proceed | Waiting for dependency, decision, or resource |
| **COMPLETED** | Work finished | Ready for review or merged |

---

## Workflow Integration

This command integrates with workflows at key transition points:

| Workflow | Step | Transition |
|----------|------|------------|
| Feature Development | Step 1 | Create ticket (PENDING) |
| Feature Development | Step 2 | `/update-status {id} IN_PROGRESS --branch ...` |
| Feature Development | Step 6 | `/update-status {id} COMPLETED` |
| Bug Fix | Step 1 | Create ticket (PENDING) |
| Bug Fix | Step 2 | `/update-status {id} IN_PROGRESS --branch ...` |
| Bug Fix | Step 9 | `/update-status {id} COMPLETED` |
| Code Review | Step 7 | `/update-status {id} COMPLETED` (after merge) |

---

## Related Commands

- `/create-ticket` - Create new tickets (use first)
- `/close-ticket` - Complete with checklist verification (if available)

## Related Workflows

- [Feature Development](../workflows/feature-development/WORKFLOW.md) - Full feature workflow
- [Bug Fix](../workflows/bug-fix/WORKFLOW.md) - Bug fixing workflow
- [Code Review Process](../workflows/code-review-process/WORKFLOW.md) - PR and merge workflow

---

*Proto Gear `/update-status` Command v1.0 - Stable*
