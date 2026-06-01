# Test-Driven Development Skill

## Overview

Test-Driven Development (TDD) is a software development approach where tests are written **before** implementation code. This skill provides patterns for practicing TDD effectively across different testing levels.

## Core Philosophy

> **Red → Green → Refactor**

1. **Red**: Write a failing test
2. **Green**: Write minimal code to pass
3. **Refactor**: Improve code while keeping tests green

## When to Use This Skill

Use TDD when:
- ✅ Implementing new features
- ✅ Fixing bugs (write test that reproduces bug first)
- ✅ Refactoring existing code
- ✅ Building critical business logic
- ✅ Working on code with complex requirements

Consider alternatives when:
- ❌ Prototyping/exploratory coding
- ❌ UI styling and layout
- ❌ Simple configuration changes
- ❌ Documentation-only updates

## Testing Pyramid

```
        ┌─────────┐
        │   E2E   │  ← Few (slow, expensive)
        ├─────────┤
        │Integration│  ← Some (moderate cost)
        ├─────────┤
        │  Unit   │  ← Many (fast, cheap)
        └─────────┘
```

- **Unit Tests**: 70% - Test individual functions/methods
- **Integration Tests**: 20% - Test component interactions
- **E2E Tests**: 10% - Test complete user workflows

## Red-Green-Refactor Cycle

### Step 1: RED - Write Failing Test

**Purpose**: Define expected behavior before implementation

**Example** (Python):
```python
# tests/test_auth.py
def test_authenticate_user_with_valid_credentials():
    """Test that valid credentials authenticate successfully"""
    # Arrange
    user = User(username="alice", password_hash=hash_password("secret123"))
    auth_service = AuthService()

    # Act
    result = auth_service.authenticate("alice", "secret123")

    # Assert
    assert result.success is True
    assert result.user.username == "alice"
```

**Key Points**:
- Write test FIRST, before implementation exists
- Test should FAIL (red) because code doesn't exist yet
- Use descriptive test names that document behavior
- Follow Arrange-Act-Assert pattern

### Step 2: GREEN - Write Minimal Code

**Purpose**: Make test pass with simplest possible implementation

**Example** (Python):
```python
# src/auth_service.py
class AuthService:
    def authenticate(self, username: str, password: str):
        # Simplest code that makes test pass
        user = User.find_by_username(username)
        if user and user.verify_password(password):
            return AuthResult(success=True, user=user)
        return AuthResult(success=False, user=None)
```

**Key Points**:
- Write ONLY enough code to pass the test
- Don't optimize or add extra features yet
- Run test - it should PASS (green)
- Resist urge to over-engineer

### Step 3: REFACTOR - Improve Code

**Purpose**: Clean up code while maintaining passing tests

**Example** (Python):
```python
# Refactored version with better structure
class AuthService:
    def authenticate(self, username: str, password: str):
        user = self._find_user(username)

        if not user:
            return self._failed_auth()

        if not user.verify_password(password):
            return self._failed_auth()

        return self._successful_auth(user)

    def _find_user(self, username: str):
        return User.find_by_username(username)

    def _failed_auth(self):
        return AuthResult(success=False, user=None)

    def _successful_auth(self, user: User):
        return AuthResult(success=True, user=user)
```

**Key Points**:
- Improve readability, structure, naming
- Extract methods for clarity
- Remove duplication
- Tests must STILL PASS after refactoring

## Test Organization

### Directory Structure

**Python**:
```
project/
├── src/
│   └── auth/
│       └── auth_service.py
└── tests/
    ├── unit/
    │   └── auth/
    │       └── test_auth_service.py
    ├── integration/
    │   └── test_auth_flow.py
    └── e2e/
        └── test_login_journey.py
```

**JavaScript/Node.js**:
```
project/
├── src/
│   └── auth/
│       └── authService.js
└── tests/
    ├── unit/
    │   └── auth/
    │       └── authService.test.js
    ├── integration/
    │   └── authFlow.test.js
    └── e2e/
        └── loginJourney.test.js
```

### Test Naming Convention

**Python**:
```python
def test_<function_name>_<scenario>_<expected_result>():
    """
    Format: test_WHAT_WHEN_EXPECTED

    Examples:
    - test_authenticate_with_valid_credentials_returns_success()
    - test_authenticate_with_invalid_password_returns_failure()
    - test_authenticate_with_nonexistent_user_returns_failure()
    """
    pass
```

**JavaScript**:
```javascript
describe('AuthService', () => {
  describe('authenticate', () => {
    it('returns success with valid credentials', () => {
      // test implementation
    });

    it('returns failure with invalid password', () => {
      // test implementation
    });
  });
});
```

## Coverage Targets

| Test Type | Coverage Target | Rationale |
|-----------|----------------|-----------|
| Unit | 80-90% | Core logic should be thoroughly tested |
| Integration | 60-70% | Key interactions covered |
| E2E | 40-50% | Critical user paths only |
| **Overall** | **70%+** | Healthy test coverage |

## Running Tests

### Python (pytest)
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/auth/test_auth_service.py

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run tests matching pattern
pytest -k "auth"

# Run only failed tests
pytest --lf
```

### JavaScript (Jest)
```bash
# Run all tests
npm test

# Run specific test file
npm test -- authService.test.js

# Run with coverage
npm test -- --coverage

# Run tests matching pattern
npm test -- --testNamePattern="auth"

# Run in watch mode
npm test -- --watch
```

### Java (JUnit)
```bash
# Maven
mvn test

# Gradle
./gradlew test

# Run specific test class
mvn test -Dtest=AuthServiceTest
```

## Best Practices

### DO ✅
- Write test before implementation
- Keep tests simple and focused
- Use descriptive test names
- Follow Arrange-Act-Assert pattern
- Test edge cases and error conditions
- Keep tests independent (no shared state)
- Run tests frequently during development

### DON'T ❌
- Write tests after implementation
- Test implementation details (test behavior)
- Create test interdependencies
- Ignore failing tests
- Skip refactoring step
- Write overly complex tests
- Mock everything (test real interactions when possible)

## Language-Specific Examples

### Python (pytest)
```python
import pytest
from src.calculator import Calculator

class TestCalculator:
    def setup_method(self):
        """Runs before each test"""
        self.calc = Calculator()

    def test_add_positive_numbers_returns_sum(self):
        """Adding 2 + 3 should return 5"""
        result = self.calc.add(2, 3)
        assert result == 5

    def test_divide_by_zero_raises_exception(self):
        """Dividing by zero should raise ValueError"""
        with pytest.raises(ValueError):
            self.calc.divide(10, 0)
```

### JavaScript (Jest)
```javascript
const Calculator = require('./calculator');

describe('Calculator', () => {
  let calc;

  beforeEach(() => {
    calc = new Calculator();
  });

  it('adds positive numbers and returns sum', () => {
    const result = calc.add(2, 3);
    expect(result).toBe(5);
  });

  it('throws error when dividing by zero', () => {
    expect(() => {
      calc.divide(10, 0);
    }).toThrow('Cannot divide by zero');
  });
});
```

### Java (JUnit 5)
```java
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.BeforeEach;
import static org.junit.jupiter.api.Assertions.*;

class CalculatorTest {
    private Calculator calc;

    @BeforeEach
    void setUp() {
        calc = new Calculator();
    }

    @Test
    void addPositiveNumbersReturnsSum() {
        int result = calc.add(2, 3);
        assertEquals(5, result);
    }

    @Test
    void divideByZeroThrowsException() {
        assertThrows(ArithmeticException.class, () -> {
            calc.divide(10, 0);
        });
    }
}
```

## Integration with PROJECT_STATUS.md

When practicing TDD, update PROJECT_STATUS.md to track test coverage:

```yaml
metrics:
  test_coverage: 78%
  unit_tests: 234
  integration_tests: 45
  e2e_tests: 12
```

## Related Capabilities

- **Workflow**: [Feature Development](../../workflows/feature-development.md) - Uses TDD throughout
- **Command**: [Run Tests](../../commands/run-tests.md) - Execute test suite (if available)
- **Workflow**: [Bug Fix](../../workflows/bug-fix.md) - Write test that reproduces bug (if available)

## Further Reading

- Refer to TESTING.md in project root for project-specific conventions
- See PROJECT_STATUS.md for current test coverage metrics
- Check your project's test runner documentation for advanced options

---
*Proto Gear Testing Skill v1.0 - Stable*
