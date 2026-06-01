# Code Review Skill

## Overview

Code review is the systematic examination of source code to find bugs, improve quality, share knowledge, and maintain standards. This skill covers both reviewing others' code and having your code reviewed effectively.

## Core Philosophy

> **Review code, not people. Focus on improvement, not criticism.**

Code review is collaboration, not confrontation. The goal is better code and better developers.

## When to Use This Skill

Perform code reviews when:
- ✅ Pull requests are submitted
- ✅ Before merging to main branch
- ✅ Pairing on critical features
- ✅ Onboarding new team members
- ✅ Implementing complex logic
- ✅ Security-sensitive changes

Skip formal review for:
- ❌ Trivial changes (typos, formatting)
- ❌ Automated dependency updates
- ❌ Documentation-only changes
- ❌ Emergency hotfixes (review after)

---

## Code Review Checklist

### 1. Functionality ✅

**Does the code work?**
- [ ] Implements stated requirements
- [ ] Handles edge cases
- [ ] Error handling present
- [ ] No obvious bugs
- [ ] Logic is sound

**Example Questions**:
```
- What happens if input is null?
- What if the list is empty?
- What if the API call fails?
- What about concurrent access?
```

### 2. Tests 🧪

**Is the code tested?**
- [ ] Tests exist and pass
- [ ] Tests cover happy path
- [ ] Tests cover edge cases
- [ ] Tests are meaningful
- [ ] Coverage is adequate

**Example Review Comment**:
```markdown
**Suggestion**: Add test for empty input case

```python
def test_empty_input():
    result = process_data([])
    assert result == []
```

This ensures the function handles edge cases gracefully.
```

### 3. Design 🏗️

**Is the code well-designed?**
- [ ] Single Responsibility Principle
- [ ] DRY (Don't Repeat Yourself)
- [ ] Appropriate abstractions
- [ ] Reasonable complexity
- [ ] Follows project patterns

**Red Flags**:
- Functions > 50 lines
- Deeply nested logic (>3 levels)
- God classes/functions
- Tight coupling
- Magic numbers

### 4. Readability 📖

**Is the code easy to understand?**
- [ ] Clear variable names
- [ ] Descriptive function names
- [ ] Logical structure
- [ ] Comments where needed
- [ ] No cryptic abbreviations

**Example - Before**:
```python
def p(d):  # BAD: unclear names
    r = []
    for i in d:
        if i['s'] == 'a':
            r.append(i)
    return r
```

**Example - After**:
```python
def get_active_users(users):  # GOOD: clear intent
    active_users = []
    for user in users:
        if user['status'] == 'active':
            active_users.append(user)
    return active_users
```

### 5. Performance ⚡

**Is the code efficient?**
- [ ] No obvious inefficiencies
- [ ] Appropriate algorithms
- [ ] Database queries optimized
- [ ] No unnecessary loops
- [ ] Resources cleaned up

**Example Issue**:
```python
# ❌ BAD: N+1 query problem
for user in users:
    user.posts = fetch_posts(user.id)  # N database calls!

# ✅ GOOD: Single query
posts_by_user = fetch_all_posts([u.id for u in users])
for user in users:
    user.posts = posts_by_user.get(user.id, [])
```

### 6. Security 🔒

**Is the code secure?**
- [ ] Input validation
- [ ] Output encoding
- [ ] No hardcoded secrets
- [ ] SQL injection prevented
- [ ] XSS prevented
- [ ] CSRF protection
- [ ] Authentication/authorization

**Example Security Issue**:
```python
# ❌ SECURITY RISK: SQL injection
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# ✅ SECURE: Parameterized query
query = "SELECT * FROM users WHERE name = ?"
cursor.execute(query, (user_input,))
```

### 7. Documentation 📝

**Is the code documented?**
- [ ] Complex logic explained
- [ ] Public APIs documented
- [ ] TODOs have context
- [ ] Breaking changes noted
- [ ] README updated if needed

---

## Review Guidelines for Reviewers

### Be Constructive

❌ **Bad**: "This code is terrible."

✅ **Good**: "Consider using a dictionary here for O(1) lookup instead of O(n) list search."

### Explain Why

❌ **Bad**: "Don't do this."

✅ **Good**: "Avoid storing passwords in plaintext because it violates security best practices. Use bcrypt for password hashing."

### Offer Solutions

❌ **Bad**: "This won't scale."

✅ **Good**: "This approach loads all items into memory. For large datasets, consider pagination:
```python
def get_items_paginated(page=1, per_page=100):
    offset = (page - 1) * per_page
    return db.query().limit(per_page).offset(offset)
```"

### Praise Good Work

✅ "Nice use of list comprehension here - very readable!"
✅ "Great test coverage on edge cases!"
✅ "This abstraction makes the code much cleaner."

### Use Review Labels

**Blocking** (must fix):
- Security vulnerabilities
- Breaking changes
- Bugs
- Failing tests

**Non-blocking** (nice to have):
- Code style improvements
- Performance optimizations
- Refactoring suggestions
- Documentation additions

**Nitpick** (minor):
- Naming preferences
- Code organization
- Comment improvements

---

## Review Guidelines for Authors

### Before Requesting Review

**Self-Review First**:
1. Read your own diff
2. Check for debug code
3. Verify tests pass
4. Run linter
5. Update documentation

**Provide Context**:
```markdown
## What
Adds user authentication with JWT tokens

## Why
Users need secure login (closes #123)

## How
- Implemented JWT generation in auth.py
- Added middleware for token validation
- Created login/logout endpoints

## Testing
- Added 15 unit tests
- Manual testing: login, logout, protected routes
- All tests passing

## Screenshots
[If UI changes]

## Checklist
- [x] Tests added
- [x] Documentation updated
- [x] No breaking changes
```

### Responding to Feedback

✅ **Do**:
- Thank reviewers
- Ask for clarification if unclear
- Implement valid suggestions
- Explain decisions respectfully

❌ **Don't**:
- Take it personally
- Argue defensively
- Ignore feedback
- Make changes without discussion

**Example Response**:
```markdown
> Consider using a Set instead of List for faster lookups

Good catch! Changed to Set. However, I kept List for `recent_items`
because we need to maintain insertion order and duplicates are rare.

Updated in commit abc123.
```

---

## Review Process

### 1. Initial Scan (2-5 minutes)

Quick pass to understand:
- What problem does this solve?
- What approach was taken?
- How large is the change?
- Are tests included?

### 2. Detailed Review (10-30 minutes)

Deep dive:
- Read code carefully
- Check against checklist
- Look for issues
- Consider alternatives
- Add comments

### 3. Summary and Decision

**Approve** ✅:
- Code meets standards
- Tests pass
- No blocking issues

**Request Changes** 🔄:
- Issues found
- Changes needed
- Re-review required

**Comment** 💬:
- Questions/suggestions
- Not blocking approval

---

## Common Review Patterns

### Pattern 1: The Defensive Check

**Review for**:
```python
# Missing null check
user = get_user(id)
name = user.name  # What if user is None?

# Suggest
user = get_user(id)
if user is None:
    return error_response("User not found")
name = user.name
```

### Pattern 2: The Resource Leak

**Review for**:
```python
# File not closed
f = open('file.txt')
data = f.read()
return data  # File never closed!

# Suggest
with open('file.txt') as f:
    data = f.read()
return data
```

### Pattern 3: The Magic Number

**Review for**:
```python
# Unclear constant
if len(password) < 8:  # Why 8?

# Suggest
MIN_PASSWORD_LENGTH = 8
if len(password) < MIN_PASSWORD_LENGTH:
```

---

## Anti-Patterns to Avoid

### ❌ Nitpicking

**Bad**:
```
"I prefer spaces here"
"Use single quotes not double quotes"
"This variable should be named differently"
```

**Better**: Use automated linters for style, focus on substance

### ❌ Scope Creep

**Bad**: "While you're here, can you also refactor this other module?"

**Better**: Keep PR focused. File issues for future improvements.

### ❌ Rubber Stamping

**Bad**: Approving without actually reading

**Better**: Take time to understand the code

### ❌ Blocking on Opinions

**Bad**: Demanding changes based on personal preference

**Better**: Distinguish between standards and preferences

---

## Effective Comments

### Format

```markdown
**[Type]**: [Issue description]

[Why it's an issue]

**Suggestion**:
```[language]
[code example]
```

[Additional context if needed]
```

### Examples

**Security Issue**:
```markdown
**[Security]**: Potential SQL injection vulnerability

User input is directly interpolated into SQL query, allowing
malicious input to execute arbitrary SQL.

**Suggestion**:
```python
# Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

Reference: OWASP SQL Injection Prevention
```

**Performance**:
```markdown
**[Performance]**: Inefficient loop

This loops through all items for each operation (O(n²) complexity).
For large datasets, this will be slow.

**Suggestion**:
```python
# Build lookup dictionary once
items_by_id = {item.id: item for item in items}
# Then O(1) lookups
item = items_by_id.get(id)
```
```

**Readability**:
```markdown
**[Clarity]**: Function name doesn't describe behavior

`process()` is too generic. Name should indicate what's being processed.

**Suggestion**:
```python
def process_payment_transactions(transactions):
    # Clear what this function does
```
```

---

## Metrics to Track

- Review turnaround time (target: < 24 hours)
- Number of review iterations
- Bugs found in review vs production
- Test coverage before/after review
- Time spent reviewing

---

## Key Takeaways

1. **Review for quality**, not perfection
2. **Be kind and constructive** in feedback
3. **Focus on important issues** (security, bugs, design)
4. **Teach, don't just critique**
5. **Praise good work**
6. **Respond graciously** to feedback
7. **Keep PRs small** (<400 lines ideal)
8. **Automate style checks** (linters, formatters)

---

*For AI Agents*: Use this skill when reviewing code changes. Focus on correctness, security, and maintainability. Provide specific, actionable feedback with examples. Remember: the goal is collaborative improvement, not finding fault.
