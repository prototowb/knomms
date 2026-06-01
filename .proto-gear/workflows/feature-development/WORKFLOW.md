# Feature Development Workflow

## Overview

This workflow guides you through implementing a new feature from concept to merged code, following TDD principles and Proto Gear conventions.

## Prerequisites

Before starting:
- ✅ Feature is defined and approved
- ✅ You have read AGENTS.md and understand agent roles
- ✅ PROJECT_STATUS.md is up-to-date
- ✅ You have access to Git repository
- ✅ Development environment is set up

## Workflow Steps

### Step 1: Create and Document Ticket

**Purpose**: Establish single source of truth for this feature

**Process**:
1. Read PROJECT_STATUS.md to get next ticket ID
2. Create ticket entry following command pattern: [Create Ticket](../commands/create-ticket.md)
3. Update PROJECT_STATUS.md with ticket details

**Example**:
```markdown
## 🎫 Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-042 | Add user login feature | feature | IN_PROGRESS | feature/PROJ-042-add-user-login | Backend Agent |
```

**Commands**:
```bash
# Agent reads PROJECT_STATUS.md to understand state
cat PROJECT_STATUS.md
```

### Step 2: Create Feature Branch

**Purpose**: Isolate work following Git workflow conventions

**Process**:
1. Checkout development branch
2. Pull latest changes
3. Create feature branch following naming convention
4. Verify branch creation

**Branch Naming**:
```
feature/<TICKET-ID>-<short-description>

Example: feature/PROJ-042-add-user-login
```

**Commands**:
```bash
# Ensure on development branch
git checkout development

# Pull latest
git pull origin development

# Create feature branch
git checkout -b feature/PROJ-042-add-user-login

# Verify
git branch --show-current
```

**Reference**: See [Testing Skill](../skills/testing/SKILL.md) for detailed branching patterns (or BRANCHING.md in project root)

### Step 3: Write Failing Tests (RED)

**Purpose**: Define expected behavior before implementation

**Process**:
1. Identify what needs testing (unit, integration, e2e)
2. Create test files in appropriate directories
3. Write tests that describe expected behavior
4. Run tests - they should FAIL (red)

**Example** (Python):
```python
# tests/unit/auth/test_login_feature.py
def test_login_with_valid_credentials_returns_success():
    """Users can login with correct username and password"""
    auth_service = AuthService()
    result = auth_service.login("alice", "correct_password")

    assert result.success is True
    assert result.user.username == "alice"
    assert result.session_token is not None

def test_login_with_invalid_password_returns_failure():
    """Login fails with incorrect password"""
    auth_service = AuthService()
    result = auth_service.login("alice", "wrong_password")

    assert result.success is False
    assert result.error == "Invalid credentials"
```

**Commands**:
```bash
# Run tests - should FAIL
pytest tests/unit/auth/test_login_feature.py

# Expected output: FAILED (because feature doesn't exist yet)
```

**Reference**: See [Testing Skill](../skills/testing/SKILL.md) for TDD patterns

### Step 4: Implement Feature (GREEN)

**Purpose**: Write minimal code to make tests pass

**Process**:
1. Create implementation files
2. Write simplest code that passes tests
3. Run tests frequently
4. Stop when tests PASS (green)

**Example** (Python):
```python
# src/auth/auth_service.py
class AuthService:
    def login(self, username: str, password: str):
        """Authenticate user with username and password"""
        user = User.find_by_username(username)

        if not user:
            return LoginResult(success=False, error="Invalid credentials")

        if not user.verify_password(password):
            return LoginResult(success=False, error="Invalid credentials")

        session_token = self._create_session_token(user)
        return LoginResult(success=True, user=user, session_token=session_token)
```

**Commands**:
```bash
# Run tests - should PASS
pytest tests/unit/auth/test_login_feature.py

# Expected output: PASSED
```

**Key Points**:
- Write ONLY code needed to pass tests
- Don't over-engineer or add extra features
- Focus on making tests green

### Step 5: Refactor and Improve (REFACTOR)

**Purpose**: Clean up code while maintaining passing tests

**Process**:
1. Review implementation for improvements
2. Extract methods for clarity
3. Remove duplication
4. Improve naming
5. Run tests after each change - must stay GREEN

**Example** (Python):
```python
# Refactored version
class AuthService:
    def login(self, username: str, password: str):
        """Authenticate user and create session"""
        user = self._find_and_verify_user(username, password)

        if not user:
            return self._failed_login("Invalid credentials")

        return self._successful_login(user)

    def _find_and_verify_user(self, username: str, password: str):
        user = User.find_by_username(username)
        if user and user.verify_password(password):
            return user
        return None

    def _failed_login(self, error_message: str):
        return LoginResult(success=False, error=error_message)

    def _successful_login(self, user: User):
        session_token = SessionManager.create_token(user)
        return LoginResult(success=True, user=user, session_token=session_token)
```

**Commands**:
```bash
# Run tests after refactoring - should STILL PASS
pytest tests/unit/auth/test_login_feature.py

# Run full test suite
pytest
```

**Best Practices**:
- Refactor in small steps
- Run tests after each change
- If tests fail, undo last change
- Commit when tests pass

### Step 6: Commit Changes

**Purpose**: Save work with descriptive commit message

**Process**:
1. Stage relevant files
2. Write conventional commit message
3. Reference ticket ID in message
4. Push to remote (if applicable)

**Commit Message Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**: feat, fix, docs, refactor, test, chore

**Example**:
```bash
# Stage files
git add src/auth/auth_service.py
git add tests/unit/auth/test_login_feature.py

# Commit with conventional message
git commit -m "feat(auth): add user login feature

Implements user authentication with username/password.
Includes unit tests with 90% coverage.

Tests:
- Valid credentials → successful login
- Invalid password → failure with error
- Nonexistent user → failure with error

Closes PROJ-042"

# Push to remote
git push -u origin feature/PROJ-042-add-user-login
```

**Reference**: See BRANCHING.md in project root for commit conventions

### Step 7: Update Status and Create PR

**Purpose**: Track progress and request review

**Process**:
1. Update PROJECT_STATUS.md to mark ticket completed
2. Create pull request
3. Fill out PR template
4. Request review (if team workflow requires)

**Update PROJECT_STATUS.md**:
```markdown
## ✅ Completed Tickets

| ID | Title | Completed | PR |
|----|-------|-----------|-----|
| PROJ-042 | Add user login feature | 2025-11-05 | #123 |
```

**Create Pull Request** (if using GitHub):
```bash
# Using GitHub CLI (if available)
gh pr create \
  --title "feat(auth): add user login feature" \
  --body "Implements user authentication. Closes PROJ-042" \
  --base development
```

**PR Description Template**:
```markdown
## Summary
Implements user login feature with username/password authentication.

## Changes Made
- Added `AuthService.login()` method
- Created unit tests for login scenarios
- Implemented session token generation

## Testing Done
- ✅ All unit tests passing (3/3)
- ✅ Test coverage: 92%
- ✅ Manual testing in dev environment

## Checklist
- [x] Tests written and passing
- [x] Code refactored and clean
- [x] PROJECT_STATUS.md updated
- [x] Follows Git workflow conventions
- [x] No security vulnerabilities introduced

Closes PROJ-042
```

## Success Criteria

Feature development is complete when:
- ✅ All tests passing (unit, integration, e2e as applicable)
- ✅ Test coverage meets target (70%+)
- ✅ Code follows project conventions
- ✅ No linting errors
- ✅ PROJECT_STATUS.md updated
- ✅ Pull request created
- ✅ CI/CD pipeline passing (if applicable)

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Writing implementation before tests | Stop and write tests first |
| Skipping refactoring step | Always refactor after green |
| Vague commit messages | Follow conventional commit format |
| Not updating PROJECT_STATUS.md | Update after each major step |
| Over-engineering features | Write minimal code to pass tests |
| Not running tests frequently | Run tests after every small change |

## Variations

### For Bug Fixes
Use [Bug Fix Workflow](bug-fix.md) instead (if available)

### For Refactoring
Use [Refactoring Workflow](refactoring.md) instead (if available)

### For Performance Work
Use [Performance Optimization Workflow](performance-optimization.md) instead (if available)

## Integration with Core Templates

- **AGENTS.md**: Agent roles coordinate feature work
- **PROJECT_STATUS.md**: Single source of truth for ticket status
- **BRANCHING.md**: Git workflow conventions
- **TESTING.md**: TDD methodology details

## Tools and Native Commands

This workflow uses native development tools:
- `git` - Version control
- `pytest` / `npm test` / `mvn test` - Testing (project-specific)
- `gh` - GitHub CLI (if using GitHub)
- Text editor - Code editing

## Related Capabilities

- **Skill**: [Testing](../skills/testing/SKILL.md) - TDD patterns
- **Command**: [Create Ticket](../commands/create-ticket.md) - Ticket documentation
- **Workflow**: [Bug Fix](bug-fix.md) - Alternative for defects (if available)
- **Workflow**: [Refactoring](refactoring.md) - Code quality improvements (if available)

## Language-Specific Notes

### Python Projects
- Tests in `tests/` directory
- Use `pytest` for test execution
- Follow PEP 8 style guide

### JavaScript/Node.js Projects
- Tests alongside source or in `__tests__/`
- Use `jest` or `mocha` for testing
- Follow ESLint configuration

### Java Projects
- Tests in `src/test/java/`
- Use JUnit for testing
- Follow project's checkstyle rules

---
*Proto Gear Feature Development Workflow v1.0 - Stable*
