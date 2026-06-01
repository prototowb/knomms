{{python_examples}}

{{nodejs_examples}}


---

<!-- proto-gear:header
purpose: TDD methodology, test pyramid, coverage targets
read-when: When writing tests or assessing coverage
priority: recommended
defines:
  - red-green-refactor-cycle
  - test-pyramid
  - coverage-targets
  - testing-conventions
links:
  - AGENTS.md
  - .proto-gear/skills/testing
-->
# TESTING.md - Test-Driven Development Workflow

## 📚 Related Documentation

This file is part of the Proto Gear documentation system. For complete context, also review:

- **AGENTS.md** - Agent workflows, collaboration patterns, and capability discovery
- **PROJECT_STATUS.md** - Current project state, active tickets, sprint info
- **BRANCHING.md** (if exists) - Git workflow, branch naming, commit conventions
- **.proto-gear/INDEX.md** (if exists) - Available capabilities and testing workflows
- **.proto-gear/skills/testing/** (if exists) - Advanced TDD patterns and techniques

---

## Testing Philosophy

### Test-Driven Development (TDD)

We follow the **Red-Green-Refactor** cycle:

```
🔴 RED    → Write a failing test
🟢 GREEN  → Write minimal code to make it pass
🔵 REFACTOR → Improve code while keeping tests green
```

**Benefits:**
- Better design through test-first thinking
- Higher code coverage from the start
- Living documentation of expected behavior
- Faster debugging (tests catch issues immediately)
- Confidence in refactoring

---

## Test Types & Structure

### Test Pyramid

```
        /\
       /  \      E2E Tests (Few)
      /____\     - Full user workflows
     /      \    - Critical paths only
    /        \
   /  INTEG.  \  Integration Tests (Some)
  /____________\ - Module interactions
 /              \ - External dependencies
/________________\
   UNIT TESTS     Unit Tests (Many)
                  - Individual functions
                  - Edge cases
                  - Fast & isolated
```

### 1. Unit Tests

**Purpose**: Test individual functions/classes in isolation

**Characteristics:**
- ✅ Fast (< 1ms per test)
- ✅ No external dependencies (databases, APIs, filesystem)
- ✅ Use mocks/stubs for dependencies
- ✅ Test one thing at a time

**Example Structure:**
```python
# test_{{MODULE_NAME}}.py

import pytest
from .{{MODULE_NAME}} import calculate_total

class TestCalculateTotal:
    """Test suite for calculate_total function"""

    def test_empty_cart_returns_zero(self):
        """Empty cart should return 0"""
        result = calculate_total([])
        assert result == 0

    def test_single_item_returns_item_price(self):
        """Single item should return its price"""
        items = [{"price": 10.00}]
        result = calculate_total(items)
        assert result == 10.00

    def test_multiple_items_returns_sum(self):
        """Multiple items should return sum of prices"""
        items = [
            {"price": 10.00},
            {"price": 20.00},
            {"price": 5.50}
        ]
        result = calculate_total(items)
        assert result == 35.50

    def test_negative_prices_raise_error(self):
        """Negative prices should raise ValueError"""
        items = [{"price": -10.00}]
        with pytest.raises(ValueError):
            calculate_total(items)
```

**Coverage Target**: 80-90% of unit-testable code

---

### 2. Integration Tests

**Purpose**: Test how modules work together

**Characteristics:**
- ⚠️ Slower than unit tests (< 100ms per test)
- ✅ Test real interactions between components
- ✅ May use test databases, mock APIs
- ✅ Verify data flows correctly

**Example Structure:**
```python
# test_{{MODULE_NAME}}_integration.py

import pytest
from .api import create_user
from .database import UserRepository

class TestUserCreationFlow:
    """Integration tests for user creation"""

    @pytest.fixture
    def test_db(self):
        """Setup test database"""
        # Create test DB, yield, cleanup
        pass

    def test_create_user_stores_in_database(self, test_db):
        """User creation should persist to database"""
        # Arrange
        user_data = {"email": "test@example.com", "name": "Test"}

        # Act
        user_id = create_user(user_data)

        # Assert
        repo = UserRepository(test_db)
        user = repo.get_by_id(user_id)
        assert user.email == "test@example.com"
```

**Coverage Target**: 60-70% of integration paths

---

### 3. End-to-End (E2E) Tests

**Purpose**: Test complete user workflows

**Characteristics:**
- 🐌 Slow (seconds per test)
- ✅ Test real system behavior
- ✅ Use real or staging environment
- ✅ Verify critical user journeys

**Example Structure:**
```python
# test_{{WORKFLOW_NAME}}_e2e.py

import pytest
from selenium import webdriver

class TestCheckoutWorkflow:
    """E2E test for complete checkout flow"""

    def test_user_can_purchase_item(self, browser):
        """User should complete purchase from search to confirmation"""
        # Navigate to site
        browser.get("{{BASE_URL}}")

        # Search for product
        browser.find_element_by_id("search").send_keys("laptop")
        browser.find_element_by_id("search-btn").click()

        # Add to cart
        browser.find_element_by_class("add-to-cart").click()

        # Checkout
        browser.find_element_by_id("checkout-btn").click()

        # Fill payment info (test credentials)
        # ...

        # Verify success
        confirmation = browser.find_element_by_class("order-confirmation")
        assert "Thank you for your order" in confirmation.text
```

**Coverage Target**: 100% of critical user paths

---

## TDD Workflow: The Red-Green-Refactor Cycle

### Step-by-Step Process

#### 🔴 Phase 1: RED (Write Failing Test)

**Before writing ANY implementation code:**

1. **Understand the requirement**
   ```
   Feature: User authentication
   Requirement: Users can log in with email and password
   ```

2. **Write the test FIRST**
   ```python
   def test_user_can_login_with_valid_credentials(self):
       """Valid credentials should authenticate user"""
       # Arrange
       user = User.create(email="test@example.com", password="secret123")

       # Act
       result = authenticate(email="test@example.com", password="secret123")

       # Assert
       assert result.success is True
       assert result.user.email == "test@example.com"
   ```

3. **Run the test** - It MUST fail
   ```bash
   pytest tests/test_auth.py::test_user_can_login_with_valid_credentials -v
   ```

   **Expected output:**
   ```
   FAILED - NameError: name 'authenticate' is not defined
   ```

**Why this matters:**
- Confirms test is actually testing something
- Prevents false positives (tests that always pass)
- Validates test setup is correct

---

#### 🟢 Phase 2: GREEN (Make Test Pass)

**Write MINIMAL code to make test pass:**

```python
def authenticate(email: str, password: str) -> AuthResult:
    """Authenticate user with email and password"""
    user = User.get_by_email(email)

    if user and user.check_password(password):
        return AuthResult(success=True, user=user)

    return AuthResult(success=False, user=None)
```

**Run the test again:**
```bash
pytest tests/test_auth.py::test_user_can_login_with_valid_credentials -v
```

**Expected output:**
```
PASSED ✅
```

**Key principle**: Don't add features not covered by tests!

---

#### 🔵 Phase 3: REFACTOR (Improve Code)

**Now improve the code while keeping tests green:**

```python
# Refactor for better error handling
def authenticate(email: str, password: str) -> AuthResult:
    """
    Authenticate user with email and password.

    Args:
        email: User's email address
        password: User's password (plaintext)

    Returns:
        AuthResult with success status and user object

    Raises:
        ValueError: If email or password is empty
    """
    if not email or not password:
        raise ValueError("Email and password are required")

    user = User.get_by_email(email)

    if user and user.check_password(password):
        logger.info(f"User {email} authenticated successfully")
        return AuthResult(success=True, user=user)

    logger.warning(f"Failed authentication attempt for {email}")
    return AuthResult(success=False, user=None)
```

**Run ALL tests to ensure nothing broke:**
```bash
pytest tests/ -v
```

**All tests should still pass!** ✅

---

### TDD Workflow Checklist

For every new feature or bug fix:

- [ ] **1. Write failing test** (RED)
  - [ ] Test describes expected behavior
  - [ ] Test fails when run
  - [ ] Failure message is clear

- [ ] **2. Write minimal implementation** (GREEN)
  - [ ] Test now passes
  - [ ] No extra features added
  - [ ] Code is simplest solution

- [ ] **3. Refactor if needed** (REFACTOR)
  - [ ] Improve code quality
  - [ ] All tests still pass
  - [ ] No behavior changes

- [ ] **4. Commit changes**
  - [ ] Tests committed WITH implementation
  - [ ] Coverage maintained or improved
  - [ ] CI/CD passes

---

## Coverage Targets

### Overall Coverage Goals

| Coverage Type | Target | Minimum |
|---------------|--------|---------|
| **Line Coverage** | {{COVERAGE_TARGET}}% | 70% |
| **Branch Coverage** | 75% | 60% |
| **Function Coverage** | 90% | 80% |

### Per-Module Targets

```python
# pytest.ini or .coveragerc
[coverage:run]
source = {{SOURCE_DIR}}
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[coverage:report]
fail_under = {{COVERAGE_TARGET}}
show_missing = True
skip_covered = False

[coverage:html]
directory = htmlcov
```

### Running Coverage

```bash
# Run tests with coverage
{{TEST_COMMAND}} --cov={{SOURCE_DIR}} --cov-report=term-missing

# Generate HTML report
{{TEST_COMMAND}} --cov={{SOURCE_DIR}} --cov-report=html

# Fail if coverage below threshold
{{TEST_COMMAND}} --cov={{SOURCE_DIR}} --cov-fail-under={{COVERAGE_TARGET}}
```

---

## Test Organization

### Directory Structure

```
{{PROJECT_ROOT}}/
├── {{SOURCE_DIR}}/
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   └── services.py
│   └── api/
│       ├── __init__.py
│       └── routes.py
│
└── tests/
    ├── unit/
    │   ├── test_auth_models.py
    │   └── test_auth_services.py
    ├── integration/
    │   └── test_auth_flow.py
    ├── e2e/
    │   └── test_login_workflow.py
    ├── fixtures/
    │   └── sample_data.py
    └── conftest.py  # Shared fixtures
```

### File Naming Conventions

| Pattern | Usage |
|---------|-------|
| `test_{{module}}.py` | Unit tests for module |
| `test_{{module}}_integration.py` | Integration tests |
| `test_{{workflow}}_e2e.py` | End-to-end tests |
| `conftest.py` | Pytest fixtures and configuration |

---

## Testing Best Practices

### ✅ DO

1. **Write tests first** (TDD)
   ```python
   # ✅ Good: Test written before implementation
   def test_calculate_discount():
       assert calculate_discount(100, 0.1) == 90
   ```

2. **Test one thing per test**
   ```python
   # ✅ Good: Focused test
   def test_empty_cart_total_is_zero():
       assert Cart().total() == 0

   # ✅ Good: Separate test for different concern
   def test_cart_with_items_sums_prices():
       cart = Cart([Item(10), Item(20)])
       assert cart.total() == 30
   ```

3. **Use descriptive test names**
   ```python
   # ✅ Good: Clear what's being tested
   def test_user_cannot_login_with_wrong_password():
       pass

   # ❌ Bad: Vague
   def test_login():
       pass
   ```

4. **Follow Arrange-Act-Assert pattern**
   ```python
   def test_user_creation():
       # Arrange - Set up test data
       email = "test@example.com"
       password = "secret"

       # Act - Execute the code being tested
       user = User.create(email=email, password=password)

       # Assert - Verify the results
       assert user.email == email
       assert user.password != password  # Should be hashed
   ```

5. **Use fixtures for common setup**
   ```python
   # conftest.py
   @pytest.fixture
   def sample_user():
       return User(email="test@example.com", name="Test User")

   # test_user.py
   def test_user_has_email(sample_user):
       assert sample_user.email == "test@example.com"
   ```

6. **Mock external dependencies**
   ```python
   from unittest.mock import patch, Mock

   @patch('.api.requests.get')
   def test_fetch_user_data(mock_get):
       # Arrange
       mock_get.return_value = Mock(status_code=200, json=lambda: {"id": 1})

       # Act
       user_data = fetch_user_from_api(user_id=1)

       # Assert
       assert user_data["id"] == 1
       mock_get.assert_called_once()
   ```

### ❌ DON'T

1. **Don't write tests after implementation**
   ```python
   # ❌ Bad: Implementation-first approach
   # 1. Write calculate_discount()
   # 2. Then write tests
   ```

2. **Don't test multiple things in one test**
   ```python
   # ❌ Bad: Too many concerns
   def test_user_workflow():
       user = create_user()
       user.login()
       user.update_profile()
       user.delete_account()
       # Hard to debug when this fails!
   ```

3. **Don't depend on test execution order**
   ```python
   # ❌ Bad: Test depends on previous test
   def test_create_user():
       global user_id
       user_id = User.create().id

   def test_update_user():
       User.update(user_id, name="New Name")  # Breaks if test_create_user didn't run!
   ```

4. **Don't use real external services in unit tests**
   ```python
   # ❌ Bad: Hits real API
   def test_weather_api():
       response = requests.get("https://api.weather.com/forecast")
       assert response.status_code == 200

   # ✅ Good: Use mock
   @patch('requests.get')
   def test_weather_api(mock_get):
       mock_get.return_value = Mock(status_code=200)
       # Test your code, not external API
   ```

---

## CI/CD Integration

### Pre-commit Checks

**Run before EVERY commit:**

```bash
# Run tests
{{TEST_COMMAND}} tests/ -v

# Check coverage
{{TEST_COMMAND}} tests/ --cov={{SOURCE_DIR}} --cov-fail-under={{COVERAGE_TARGET}}

# Run linter
{{LINTER_COMMAND}}

# Type checking (if applicable)
{{TYPE_CHECKER_COMMAND}}
```

### Git Hooks

```bash
# .git/hooks/pre-commit
#!/bin/sh

echo "🧪 Running tests before commit..."
{{TEST_COMMAND}} tests/ --cov={{SOURCE_DIR}} --cov-fail-under={{COVERAGE_TARGET}}

if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi

echo "✅ All tests passed!"
```

### CI Pipeline

**Every pull request should:**

1. ✅ Run full test suite
2. ✅ Check coverage threshold
3. ✅ Run linter
4. ✅ Run type checker (if applicable)
5. ✅ Build successfully
6. ✅ Pass security scans

**Example GitHub Actions workflow:**

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up {{LANGUAGE}}
        uses: {{SETUP_ACTION}}
        with:
          {{LANGUAGE_VERSION}}: 0.10.0

      - name: Install dependencies
        run: {{INSTALL_COMMAND}}

      - name: Run tests with coverage
        run: {{TEST_COMMAND}} tests/ --cov={{SOURCE_DIR}} --cov-report=xml

      - name: Check coverage threshold
        run: {{TEST_COMMAND}} tests/ --cov={{SOURCE_DIR}} --cov-fail-under={{COVERAGE_TARGET}}

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
```

---

## Testing Commands

### Quick Reference

```bash
# Run all tests
{{TEST_COMMAND}} tests/

# Run specific test file
{{TEST_COMMAND}} tests/unit/test_auth.py

# Run specific test
{{TEST_COMMAND}} tests/unit/test_auth.py::test_user_login

# Run with verbose output
{{TEST_COMMAND}} tests/ -v

# Run with coverage
{{TEST_COMMAND}} tests/ --cov={{SOURCE_DIR}}

# Run with coverage report
{{TEST_COMMAND}} tests/ --cov={{SOURCE_DIR}} --cov-report=html

# Run only failed tests from last run
{{TEST_COMMAND}} tests/ --lf

# Run tests in parallel (faster)
{{TEST_COMMAND}} tests/ -n auto

# Run tests matching pattern
{{TEST_COMMAND}} tests/ -k "auth"

# Show print statements
{{TEST_COMMAND}} tests/ -s

# Stop on first failure
{{TEST_COMMAND}} tests/ -x
```

---

## Resources for AI Agents

### When Writing Tests

1. **Analyze the requirement** - What behavior should exist?
2. **Write the test first** - Describe expected behavior
3. **Run the test** - Confirm it fails (RED)
4. **Implement minimal solution** - Make test pass (GREEN)
5. **Refactor if needed** - Improve while keeping green (REFACTOR)
6. **Commit with tests** - Never commit code without tests

### When Reviewing Code

1. **Check test coverage** - Is new code tested?
2. **Review test quality** - Do tests actually test behavior?
3. **Verify TDD followed** - Were tests written first?
4. **Check for edge cases** - Are error cases tested?
5. **Ensure isolation** - Do tests mock external dependencies?

### When Debugging

1. **Run specific failing test** - Isolate the problem
2. **Add assertions** - Narrow down the failure point
3. **Check test data** - Verify fixtures and mocks
4. **Review recent changes** - What changed since tests passed?
5. **Use debugger** - Step through failing test

---

## Ticket Integration

### When Creating Tickets

**Every feature ticket should include:**

```markdown
## Testing Requirements

- [ ] Unit tests for {{FEATURE_NAME}}
- [ ] Integration tests for {{WORKFLOW}}
- [ ] E2E test for {{USER_JOURNEY}}
- [ ] Coverage target: {{COVERAGE_TARGET}}%

### Test Cases

1. **Happy path**: User can {{ACTION}}
2. **Error case**: System handles {{ERROR_CONDITION}}
3. **Edge case**: {{EDGE_CASE_DESCRIPTION}}

### Acceptance Criteria

- All tests pass
- Coverage ≥ {{COVERAGE_TARGET}}%
- No new linting errors
```

### Before Closing Tickets

- [ ] All tests written BEFORE implementation
- [ ] All tests passing
- [ ] Coverage target met
- [ ] CI/CD pipeline green
- [ ] Code reviewed and approved

---

## Template Variables Reference

This template uses the following variables (replaced during `pg init`):

- `` - Your project name
- `{{TEST_FRAMEWORK}}` - Testing framework (pytest, jest, etc.)
- `{{COVERAGE_TARGET}}` - Target coverage percentage (default: 80)
- `{{SOURCE_DIR}}` - Source code directory
- `{{TEST_COMMAND}}` - Command to run tests
- `{{LINTER_COMMAND}}` - Command to run linter
- `{{TYPE_CHECKER_COMMAND}}` - Command to run type checker
- `{{LANGUAGE}}` - Programming language
- `0.10.0` - Language version

---

**Remember**: Tests are not just verification - they're documentation, design tools, and safety nets. Write them first, keep them fast, and trust them completely.

**Test-Driven Development is not just a practice - it's a discipline that leads to better code.**

---

## Ticket-Based Test Enforcement

### Mandatory Test Creation Per Ticket

Every ticket **must** have associated tests before it can be considered complete. When creating or picking up a ticket:

```python
def create_test_structure_for_ticket(ticket):
    """
    MANDATORY: Creates test files for every ticket.
    Called automatically when a ticket is created or started.
    """
    ticket_id = ticket['id']
    feature_name = ticket['slug']

    # Determine what tests to create based on your project type
    test_files = determine_test_files(ticket, feature_name)

    # Create test files
    for test_file in test_files:
        create_file(test_file, generate_test_template(feature_name))
        print(f"  Created test: {test_file}")

    # Add test requirements to ticket
    ticket['test_files'] = test_files
    ticket['test_coverage_target'] = {{MIN_COVERAGE}}  # Minimum coverage

    return test_files
```

### Pre-Merge Test Validation

Before any ticket branch can be merged, validate that tests exist and pass:

```python
def validate_tests_exist(ticket):
    """
    Ensures tests exist before allowing merge.
    """
    if not ticket.get('test_files'):
        raise ValueError(f"Ticket {ticket['id']} has no tests!")

    for test_file in ticket['test_files']:
        if not file_exists(test_file):
            raise ValueError(f"Missing test file: {test_file}")

    # Run tests
    test_results = run_tests(ticket['test_files'])
    if not test_results['passing']:
        raise ValueError(f"Tests failing for {ticket['id']}")

    # Check coverage
    if test_results['coverage'] < ticket['test_coverage_target']:
        raise ValueError(
            f"Coverage {test_results['coverage']}% below target {ticket['test_coverage_target']}%"
        )

    print(f"All tests passing with {test_results['coverage']}% coverage")
    return True
```

### Enforcement Checklist

For every ticket, before marking as complete:

- [ ] Test files created alongside implementation
- [ ] All tests passing
- [ ] Coverage meets or exceeds `{{MIN_COVERAGE}}%` target
- [ ] No regressions in existing tests
- [ ] Test names describe expected behavior clearly

---

*Generated by Proto Gear v0.10.0 - AI Agent Framework for Intelligent Development Workflows*
*Last updated: {{GENERATION_DATE}}*
