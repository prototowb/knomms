# Code Review Process Workflow

## Overview

This workflow guides the complete process of creating, reviewing, and merging pull requests. It ensures code quality through systematic review while maintaining collaboration and knowledge sharing.

## Prerequisites

Before starting:
- ✅ Feature/fix branch with committed changes
- ✅ All tests passing locally
- ✅ Code meets project style standards (linting passes)
- ✅ BRANCHING.md conventions followed
- ✅ You have read CONTRIBUTING.md (if exists)

## Core Philosophy

> **Code review is about improving code AND sharing knowledge. Every review is a learning opportunity.**

Good reviews are constructive, specific, and focused on the code, not the coder.

---

## Workflow Steps

### Step 1: Prepare for Review

**Purpose**: Ensure code is ready before requesting review

**Process**:
1. Run full test suite and verify all tests pass
2. Run linting/formatting tools
3. Self-review your own changes critically
4. Ensure commits are meaningful and follow conventions
5. Remove debug code, commented-out code, and TODOs

**Self-Review Checklist**:
- [ ] Tests pass: `npm test` / `pytest` / `go test`
- [ ] Linting passes: `npm run lint` / `flake8` / `golint`
- [ ] No console.log/print statements left for debugging
- [ ] No commented-out code
- [ ] Commits follow conventional format
- [ ] Branch is up-to-date with base branch

**Commands**:
```bash
# Run tests
npm test        # Node.js
pytest          # Python
go test ./...   # Go

# Run linting
npm run lint    # Node.js
flake8 .        # Python
golint ./...    # Go

# Verify commits
git log --oneline -5

# Update with base branch
git fetch origin development
git rebase origin/development
```

**Reference**: See TESTING.md, skills/testing

---

### Step 2: Create Pull Request

**Purpose**: Open PR with clear description for reviewers

**Process**:
1. Push your branch to remote
2. Create PR with descriptive title (follow commit conventions)
3. Fill out PR template/description thoroughly
4. Add appropriate labels (feature, bugfix, etc.)
5. Link related issues/tickets

**PR Title Format**:
```
<type>(<scope>): <description>

Examples:
feat(auth): add OAuth2 login support
fix(api): resolve null pointer in user endpoint
refactor(db): simplify connection pooling
```

**PR Description Template**:
```markdown
## Summary
Brief description of what this PR does (2-3 sentences)

## Changes
- Change 1
- Change 2
- Change 3

## Testing
How was this tested? What scenarios were verified?

## Screenshots (if UI change)
Before/After images

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated (if needed)
- [ ] No breaking changes (or noted below)

## Related Issues
Closes #123, Relates to #456
```

**Commands**:
```bash
# Push branch
git push -u origin feature/PROJ-043-add-auth

# Create PR via GitHub CLI
gh pr create --title "feat(auth): add OAuth2 login" --body "..." --base development

# Or create via web interface
# https://github.com/<owner>/<repo>/pull/new/<branch>
```

---

### Step 3: Request Review

**Purpose**: Get appropriate reviewers assigned

**Process**:
1. Identify reviewers by expertise area
2. Add reviewers to the PR
3. Notify via team channels if urgent
4. Provide context in comments if needed

**Choosing Reviewers**:
| Change Type | Suggested Reviewers |
|-------------|---------------------|
| Backend API | Backend team lead, related domain expert |
| Frontend UI | Frontend team lead, UX team member |
| Database | DBA, backend senior |
| Security | Security team member |
| Cross-cutting | Tech lead, architect |

**Commands**:
```bash
# Add reviewers via GitHub CLI
gh pr edit --add-reviewer alice,bob

# Request review via web interface
# Go to PR page -> Reviewers -> Add reviewers
```

**Etiquette**:
- Don't request review from too many people (2-3 is usually enough)
- Provide context if reviewers are unfamiliar with the area
- Be patient - reviewers have their own work too

---

### Step 4: Respond to Feedback

**Purpose**: Address reviewer comments constructively

**Process**:
1. Read all comments carefully before responding
2. Ask clarifying questions if feedback is unclear
3. Discuss alternatives if you disagree (respectfully)
4. Make requested changes
5. Push updates and respond to comments
6. Mark conversations as resolved when addressed

**Responding to Feedback**:

| Feedback Type | Response |
|---------------|----------|
| Bug/Error found | "Good catch! Fixed in abc123" |
| Style suggestion | "Makes sense, updated" or "I prefer X because Y, WDYT?" |
| Design concern | "Let me explain the reasoning... Would Z address your concern?" |
| Question | "Great question! The reason is..." |

**Commands**:
```bash
# Make changes
git add -A
git commit -m "refactor: address review feedback"
git push

# Or amend if small fix (same commit)
git add -A
git commit --amend --no-edit
git push --force-with-lease
```

**Best Practices**:
- Respond to every comment (even if just "Done")
- Don't take feedback personally
- Thank reviewers for thorough reviews
- Ask questions rather than assume

**Reference**: See skills/code-review for review best practices

---

### Step 5: Get Approval

**Purpose**: Obtain required approvals before merge

**Process**:
1. Ensure all conversations are resolved
2. Re-request review if significant changes were made
3. Wait for required number of approvals
4. Address any blocking comments

**Approval Requirements** (typical):
- 1-2 approvals for standard changes
- Team lead approval for architectural changes
- Security review for auth/security changes

**Commands**:
```bash
# Check PR status
gh pr status

# Check approval status
gh pr view --json reviews
```

**If Blocked**:
- Check for unresolved conversations
- Check for failing CI checks
- Check for merge conflicts
- Ping reviewers politely if no response after reasonable time

---

### Step 6: Merge Pull Request

**Purpose**: Merge approved changes to target branch

**Process**:
1. Verify all CI checks pass
2. Resolve any merge conflicts
3. Choose appropriate merge strategy
4. Merge the PR
5. Delete the feature branch

**Merge Strategies**:
| Strategy | When to Use |
|----------|-------------|
| **Squash merge** | Multiple small commits → clean history |
| **Merge commit** | Preserve full commit history |
| **Rebase merge** | Linear history, well-organized commits |

**Commands**:
```bash
# Merge via GitHub CLI (squash)
gh pr merge --squash --delete-branch

# Merge via GitHub CLI (merge commit)
gh pr merge --merge --delete-branch

# Merge via GitHub CLI (rebase)
gh pr merge --rebase --delete-branch
```

**Pre-Merge Checklist**:
- [ ] All CI checks passing
- [ ] Required approvals obtained
- [ ] No merge conflicts
- [ ] PR description is accurate
- [ ] Related issues will auto-close

---

### Step 7: Post-Merge Actions

**Purpose**: Complete the workflow and clean up

**Process**:
1. Verify merge completed successfully
2. Check deployment (if CI/CD triggers deployment)
3. Update ticket status to COMPLETED
4. Delete local branch
5. Notify stakeholders if needed
6. Monitor for any issues

**Commands**:
```bash
# Switch to development
git checkout development
git pull origin development

# Delete local branch
git branch -d feature/PROJ-043-add-auth

# Update ticket status
/update-status PROJ-043 COMPLETED
```

**Notification Template** (if needed):
```
Feature deployed: OAuth2 login support

PR: #123
Environment: staging/production
Changes: [brief summary]
Testing: [how to verify]
```

---

## Success Criteria

PR is successfully merged when:
- [ ] PR created with clear title and description
- [ ] All CI/CD checks passing
- [ ] Required approvals obtained
- [ ] All reviewer feedback addressed
- [ ] No unresolved conversations
- [ ] Merged to target branch
- [ ] Feature branch deleted
- [ ] Ticket status updated to COMPLETED

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Large PRs (>500 lines) | Break into smaller, focused PRs |
| Unclear PR description | Use template, explain "why" not just "what" |
| Not running tests before PR | Always run full test suite locally first |
| Ignoring reviewer feedback | Address every comment, even to disagree |
| Merging without approvals | Wait for required approvals |
| Not updating base branch | Regularly rebase/merge from development |
| Leaving dead code | Clean up before requesting review |

---

## PR Size Guidelines

| Size | Lines Changed | Review Time |
|------|---------------|-------------|
| XS | < 50 | 5-10 min |
| S | 50-200 | 15-30 min |
| M | 200-500 | 30-60 min |
| L | 500-1000 | 1-2 hours |
| XL | > 1000 | Consider splitting |

**Recommendation**: Keep PRs under 400 lines when possible. Smaller PRs get faster, better reviews.

---

## Related Skills

- [Code Review](../skills/code-review/SKILL.md) - Review expertise and checklist
- [Testing](../skills/testing/SKILL.md) - TDD and test patterns

## Related Commands

- `/update-status` - Update ticket status after merge
- `/create-ticket` - Create tickets for follow-up work

## Related Workflows

- [Feature Development](../feature-development/WORKFLOW.md) - Full feature workflow (leads into this)
- [Bug Fix](../bug-fix/WORKFLOW.md) - Bug fixing workflow (leads into this)

---

*Proto Gear Code Review Process Workflow v1.0 - Stable*
