# Bug Fix Workflow

## Overview

This workflow provides a systematic approach to investigating, fixing, and preventing software defects. It combines debugging methodology with TDD practices to ensure bugs are fixed properly and stay fixed.

## Prerequisites

Before starting:
- ✅ Bug is reported and reproducible
- ✅ You have read AGENTS.md and understand agent roles
- ✅ PROJECT_STATUS.md is up-to-date
- ✅ You have access to Git repository
- ✅ Development environment is set up

## Core Philosophy

> **Fix the root cause, not the symptom. Add tests to prevent regression.**

Bugs are opportunities to improve code quality and test coverage.

---

## Workflow Steps

### Step 1: Create Bug Ticket

**Purpose**: Document the bug and track the fix

**Process**:
1. Read PROJECT_STATUS.md to get next ticket ID
2. Create ticket with bug details
3. Include reproduction steps and expected vs actual behavior
4. Update PROJECT_STATUS.md with ticket

**Example**:
```markdown
## 🎫 Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-056 | User login fails with empty password | bug | IN_PROGRESS | bugfix/PROJ-056-login-empty-password | Backend Agent |
```

**Ticket Details Template**:
```markdown
### Bug Description
User can submit login form with empty password, causing server error

### Reproduction Steps
1. Navigate to /login
2. Enter valid username
3. Leave password field empty
4. Click "Login"
5. Server returns 500 error instead of validation error

### Expected Behavior
Client-side validation should prevent empty password submission
Server should return 400 with clear error message if validation bypassed

### Actual Behavior
Server crashes with NullPointerException on password.hash()

### Environment
- Browser: Chrome 119
- OS: Windows 11
- Version: v1.2.3
```

**Commands**:
```bash
# Read current status
cat PROJECT_STATUS.md
```

---

### Step 2: Create Bugfix Branch

**Purpose**: Isolate bug fix work following Git conventions

**Process**:
1. Checkout development branch
2. Pull latest changes
3. Create bugfix branch
4. Verify branch creation

**Branch Naming**:
```
bugfix/<TICKET-ID>-<short-description>

Example: bugfix/PROJ-056-login-empty-password
```

**Commands**:
```bash
# Ensure on development branch
git checkout development

# Pull latest
git pull origin development

# Create bugfix branch
git checkout -b bugfix/PROJ-056-login-empty-password

# Verify
git branch --show-current
```

**Reference**: See BRANCHING.md for branching conventions

---

### Step 3: Reproduce the Bug

**Purpose**: Confirm the bug exists and understand its behavior

**Process**:
1. Follow reproduction steps from bug report
2. Observe the exact error/behavior
3. Collect evidence (error messages, stack traces, logs)
4. Document observations

**Reproduction Checklist**:
- [ ] Bug reproduces consistently
- [ ] You have error messages/stack traces
- [ ] You understand what's breaking
- [ ] You can demonstrate it to others

**Commands**:
```bash
# Run the application
npm start  # or python app.py, etc.

# Run specific failing test (if exists)
pytest tests/test_login.py::test_empty_password

# Check logs
tail -f logs/app.log
```

**If Bug Doesn't Reproduce**:
- Check environment differences (versions, config, data)
- Review recent changes that might have fixed it
- Ask reporter for more details
- Document as "Cannot Reproduce" in ticket

**Reference**: See [Debugging Skill](../skills/debugging/SKILL.md) for systematic debugging techniques

---

### Step 4: Write Failing Test (RED)

**Purpose**: Create regression test that captures the bug

**Process**:
1. Write test that demonstrates the bug
2. Test should FAIL initially (proving bug exists)
3. Test describes expected behavior
4. Run test to confirm it fails

**Example** (Python):
```python
def test_login_with_empty_password_returns_validation_error():
    """
    Bug: Empty password causes server crash
    Expected: Returns 400 with validation error
    """
    # Arrange
    client = TestClient()
    data = {"username": "testuser", "password": ""}

    # Act
    response = client.post("/login", json=data)

    # Assert
    assert response.status_code == 400, "Should return 400 Bad Request"
    assert "password" in response.json()["errors"]
    assert "required" in response.json()["errors"]["password"].lower()
```

**Run Test**:
```bash
# Run the failing test
pytest tests/test_login.py::test_login_with_empty_password_returns_validation_error -v

# Expected output: FAILED (this proves the bug exists)
```

**Why This Matters**:
- Proves bug exists
- Documents expected behavior
- Prevents regression
- Guides the fix

---

### Step 5: Debug and Identify Root Cause

**Purpose**: Understand WHY the bug occurs, not just WHERE

**Process**:
1. Use debugging techniques to isolate the problem
2. Form hypothesis about root cause
3. Test hypothesis
4. Identify exact location and cause

**Debugging Approach**:

**1. Observe**:
```bash
# Add strategic logging
logging.debug(f"Login attempt: username={username}, password={'***' if password else 'EMPTY'}")
```

**2. Isolate**:
```python
# Use debugger
import pdb; pdb.set_trace()

# Or IDE breakpoints at suspected location
# Set breakpoint in login_handler() function
```

**3. Hypothesize**:
```
Hypothesis: password.hash() is called without null check
When password is empty/None, hash() method fails
```

**4. Test Hypothesis**:
```python
# Check if password can be None
print(f"Password value: {repr(password)}")  # Might print: ''
print(f"Password type: {type(password)}")   # Might print: <class 'NoneType'>
```

**Common Root Causes**:
- Missing validation
- Null/undefined checks missing
- Incorrect error handling
- Type mismatches
- Race conditions
- Edge cases not handled

**Reference**: See [Debugging Skill](../skills/debugging/SKILL.md) Step 4-5 for detailed debugging process

---

### Step 6: Fix the Bug (GREEN)

**Purpose**: Implement minimal fix that makes tests pass

**Process**:
1. Fix the root cause (not the symptom)
2. Add defensive code if needed
3. Keep changes minimal and focused
4. Run tests to verify fix

**Example Fix**:

**Before** (buggy code):
```python
def login(username, password):
    # Missing validation!
    user = get_user(username)
    if user.password_hash == hash_password(password):  # Crashes if password is None
        return create_session(user)
    return None
```

**After** (fixed code):
```python
def login(username, password):
    # Add validation
    if not username or not password:
        raise ValidationError({
            "username": "Username is required" if not username else None,
            "password": "Password is required" if not password else None
        })

    user = get_user(username)
    if user and user.password_hash == hash_password(password):
        return create_session(user)
    return None
```

**Run Tests**:
```bash
# Run the previously failing test
pytest tests/test_login.py::test_login_with_empty_password_returns_validation_error -v

# Expected output: PASSED ✅

# Run all tests to ensure no regressions
pytest tests/
```

**Fix Guidelines**:
- ✅ Fix root cause, not symptom
- ✅ Add defensive code (validation, null checks)
- ✅ Keep changes minimal
- ✅ Update error messages to be clear
- ❌ Don't refactor while fixing (separate commits)
- ❌ Don't silence errors with try/except

---

### Step 7: Verify and Test

**Purpose**: Ensure fix works and doesn't break anything else

**Verification Checklist**:
- [ ] Original bug no longer occurs
- [ ] New regression test passes
- [ ] All existing tests still pass
- [ ] Manual testing confirms correct behavior
- [ ] Edge cases are handled
- [ ] Error messages are clear and helpful

**Testing Process**:
```bash
# 1. Run specific bug test
pytest tests/test_login.py::test_login_with_empty_password_returns_validation_error -v

# 2. Run all related tests
pytest tests/test_login.py -v

# 3. Run full test suite
pytest tests/

# 4. Check coverage
pytest --cov=src --cov-report=term-missing

# 5. Manual testing
# - Test the exact reproduction steps from Step 3
# - Test edge cases (null, undefined, empty string, whitespace)
# - Test normal operation still works
```

**Manual Testing Checklist**:
- [ ] Empty password rejected with clear error
- [ ] Empty username rejected with clear error
- [ ] Valid credentials still work
- [ ] Invalid credentials handled gracefully
- [ ] UI shows appropriate error messages

---

### Step 8: Commit and Document

**Purpose**: Create clear commit with bug fix documentation

**Process**:
1. Stage changes (code + test)
2. Write descriptive commit message
3. Reference bug ticket
4. Push branch

**Commit Message Format**:
```
fix(<scope>): <short description>

<detailed description of the bug and fix>

Closes <TICKET-ID>
```

**Example**:
```bash
# Stage changes
git add src/auth/login.py tests/test_login.py

# Commit with detailed message
git commit -m "fix(auth): validate password before hashing

Bug: User login crashes with 500 error when password is empty
Root Cause: login() function calls hash_password() without validation
Fix: Add input validation that returns 400 with clear error message

Changes:
- Added validation for username and password before processing
- Returns ValidationError with field-specific messages
- Added regression test to prevent future occurrence

Closes PROJ-056"

# Push branch
git push -u origin bugfix/PROJ-056-login-empty-password
```

**Update PROJECT_STATUS.md**:
```markdown
| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-056 | User login fails with empty password | bug | COMPLETED | bugfix/PROJ-056-login-empty-password | Backend Agent |
```

---

### Step 9: Create Pull Request

**Purpose**: Get code reviewed and merged

**Process**:
1. Create PR from bugfix branch to development
2. Fill out PR template with bug details
3. Request review
4. Address feedback
5. Merge when approved

**PR Template**:
```markdown
## Bug Fix: User login fails with empty password

**Ticket**: PROJ-056

### Problem
User could submit login form with empty password, causing server to crash with 500 error.

### Root Cause
`login()` function called `hash_password()` without validating input, causing NullPointerException when password was empty/None.

### Solution
- Added input validation before password hashing
- Returns 400 with clear error message when validation fails
- Added field-specific error messages for better UX

### Testing
- ✅ Added regression test: `test_login_with_empty_password_returns_validation_error`
- ✅ All existing tests pass
- ✅ Manual testing confirms fix
- ✅ Edge cases tested (None, empty string, whitespace)

### Changes
- `src/auth/login.py` - Added validation
- `tests/test_login.py` - Added regression test

### Checklist
- [x] Tests added
- [x] All tests passing
- [x] No breaking changes
- [x] Documentation updated (if needed)
- [x] Ticket updated to COMPLETED
```

**Commands**:
```bash
# Create PR via GitHub CLI
gh pr create --title "fix(auth): validate password before hashing" \
  --body-file pr-template.md \
  --base development \
  --head bugfix/PROJ-056-login-empty-password

# Or create via web interface
# Navigate to GitHub and create PR manually
```

**Reference**: See [Code Review Skill](../skills/code-review/SKILL.md) for review best practices

---

## Post-Fix Actions

### 1. Monitor in Production

After merge:
- Watch error logs for related issues
- Monitor user reports
- Verify fix in production environment

### 2. Document Learnings

If this was a common pattern:
- Update coding guidelines
- Add to code review checklist
- Share knowledge with team
- Consider linting rule to catch similar issues

### 3. Prevent Similar Bugs

**Add Validation Framework**:
```python
# If many endpoints lack validation, create validation decorator
@validate_required(['username', 'password'])
def login(username, password):
    # Function can assume inputs are valid
```

**Add Tests**:
```python
# Create parametrized test for common edge cases
@pytest.mark.parametrize("username,password", [
    ("", "password123"),      # Empty username
    ("user", ""),              # Empty password
    (None, "password123"),    # Null username
    ("user", None),           # Null password
    ("  ", "password123"),    # Whitespace username
])
def test_login_invalid_inputs(username, password):
    with pytest.raises(ValidationError):
        login(username, password)
```

---

## Common Pitfalls

### ❌ Symptom Fixes

**Bad**:
```python
# Just catching the error
try:
    hash_password(password)
except:
    pass  # Hiding the problem!
```

**Good**:
```python
# Fixing the root cause
if not password:
    raise ValidationError("Password is required")
```

### ❌ Incomplete Testing

**Bad**:
```python
# Test passes but doesn't prevent regression
def test_login():
    assert login("user", "pass") is not None  # Too vague
```

**Good**:
```python
# Test specifically captures the bug
def test_login_with_empty_password_returns_validation_error():
    with pytest.raises(ValidationError) as exc:
        login("user", "")
    assert "password" in str(exc.value).lower()
```

### ❌ Feature + Bug Fix Together

**Bad**:
```
fix(auth): validate password AND add password strength meter
```

**Good**:
```
fix(auth): validate password before hashing

(Password strength meter is separate feature, create new ticket)
```

---

## Success Criteria

A bug fix is complete when:

- ✅ Bug no longer reproduces
- ✅ Regression test added and passing
- ✅ All tests passing
- ✅ Root cause fixed (not symptom)
- ✅ Code reviewed and approved
- ✅ Merged to development
- ✅ Ticket marked COMPLETED
- ✅ Documented in commit/PR

---

## Related Resources

- **[Debugging Skill](../skills/debugging/SKILL.md)** - Systematic debugging techniques
- **[Testing Skill](../skills/testing/SKILL.md)** - TDD and test writing
- **[Code Review Skill](../skills/code-review/SKILL.md)** - Review best practices
- **[Hotfix Workflow](hotfix.template.md)** - For critical production bugs
- **BRANCHING.md** - Git workflow conventions
- **PROJECT_STATUS.md** - Ticket tracking

---

*For AI Agents*: This workflow provides a systematic approach to bug fixes. Always write a regression test first (Step 4), fix the root cause not the symptom (Step 6), and verify thoroughly (Step 7). Bugs are opportunities to improve code quality and test coverage.
