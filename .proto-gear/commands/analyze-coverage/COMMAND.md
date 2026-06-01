# /analyze-coverage

> Run and analyze test coverage for the project

## Invocation Syntax

```
/analyze-coverage [--path DIRECTORY] [--threshold NUMBER] [--format FORMAT]
```

## Arguments

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `--path` | No | string | . | Directory to analyze |
| `--threshold` | No | number | 70 | Minimum coverage % to pass |
| `--format` | No | enum | text | Output: text, html, json, lcov |

## Examples

```
/analyze-coverage
/analyze-coverage --path src/
/analyze-coverage --threshold 80
/analyze-coverage --format html
/analyze-coverage --path tests/ --threshold 90 --format lcov
```

---

## AI Execution Steps

> **For AI Agents**: Execute these steps when `/analyze-coverage` is invoked.

### Step 1: Parse Arguments

Extract from user input:
- **--path**: Directory to analyze (default: current directory)
- **--threshold**: Minimum coverage % (default: 70)
- **--format**: Output format (default: text)

### Step 2: Detect Project Type

Read project files to detect the testing framework:
- `package.json` → JavaScript/TypeScript (Jest, Vitest)
- `pyproject.toml` / `setup.py` → Python (pytest-cov)
- `Cargo.toml` → Rust (cargo-tarpaulin)
- `go.mod` → Go (go test -cover)
- `pom.xml` / `build.gradle` → Java (JaCoCo)

### Step 3: Run Coverage Command

Execute the appropriate coverage command for the detected framework:

**JavaScript/TypeScript (Jest)**:
```bash
npm test -- --coverage --coverageDirectory=coverage
```

**Python (pytest)**:
```bash
pytest --cov={path} --cov-report=term-missing --cov-fail-under={threshold}
```

**Go**:
```bash
go test -coverprofile=coverage.out ./{path}/...
go tool cover -func=coverage.out
```

### Step 4: Parse Results

Extract coverage metrics from output:
- Line coverage %
- Branch coverage %
- Function coverage %
- Files below threshold

### Step 5: Report to User

Output summary:

```
Coverage Analysis Complete
==========================
Overall: {coverage}%
Threshold: {threshold}%
Status: {PASS/FAIL}

By Metric:
- Lines: {line_coverage}%
- Branches: {branch_coverage}%
- Functions: {function_coverage}%

{if files_below_threshold}
Files Below Threshold:
- {file1}: {coverage1}%
- {file2}: {coverage2}%
{/if}
```

---

## Completion Criteria

- [ ] Project type detected
- [ ] Coverage command executed
- [ ] Results parsed and summarized
- [ ] Pass/Fail status reported based on threshold
- [ ] Low-coverage files identified (if any)

---

## Error Handling

| Condition | Error Message |
|-----------|---------------|
| No test framework detected | "Error: Could not detect testing framework. Ensure package.json, pyproject.toml, or equivalent exists." |
| Tests fail | "Error: Tests failed. Fix failing tests before analyzing coverage." |
| Coverage tool not installed | "Error: Coverage tool not found. Install: {installation command}" |
| Invalid --format value | "Error: Invalid format '{value}'. Must be: text, html, json, lcov" |

---

## Technology Reference

The sections below provide detailed coverage commands for each technology stack.

---

## When to Use This Command

Use this command when you need to:

- **Measure Test Coverage**: Determine percentage of code tested
- **Identify Gaps**: Find untested code paths
- **Pre-Release Check**: Verify coverage before deployment
- **Code Review**: Check if new code includes tests
- **Technical Debt**: Identify areas needing more tests
- **Quality Gates**: Enforce minimum coverage thresholds
- **Continuous Integration**: Integrate coverage into CI/CD

## Quick Reference

### JavaScript/TypeScript (Jest)

**Run Coverage**:
```bash
# Basic coverage
npm test -- --coverage

# With output formats
npm test -- --coverage --coverageDirectory=coverage

# Watch mode
npm test -- --coverage --watch

# Specific files/directories
npm test path/to/tests/ -- --coverage

# Generate HTML report
npm test -- --coverage --coverageReporters=html lcov text

# View HTML report
open coverage/index.html
```

**Configure Coverage in package.json**:
```json
{
  "jest": {
    "collectCoverageFrom": [
      "src/**/*.{js,jsx,ts,tsx}",
      "!src/**/*.d.ts",
      "!src/**/*.test.{js,jsx,ts,tsx}",
      "!src/index.ts"
    ],
    "coverageThresholds": {
      "global": {
        "branches": 70,
        "functions": 70,
        "lines": 70,
        "statements": 70
      }
    },
    "coverageReporters": ["text", "lcov", "html"]
  }
}
```

**Fail on Low Coverage**:
```bash
# Fail if below thresholds
npm test -- --coverage --coverageThreshold='{"global":{"lines":70}}'
```

### JavaScript/TypeScript (Vitest)

**Run Coverage**:
```bash
# Install coverage tool
npm install -D @vitest/coverage-c8

# Run with coverage
npx vitest --coverage

# Watch mode
npx vitest --coverage --watch

# UI mode with coverage
npx vitest --ui --coverage
```

**Configure in vitest.config.ts**:
```typescript
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    coverage: {
      provider: 'c8',
      reporter: ['text', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'dist/',
        '**/*.test.ts',
        '**/*.spec.ts'
      ],
      statements: 70,
      branches: 70,
      functions: 70,
      lines: 70
    }
  }
});
```

### Python (pytest + coverage.py)

**Run Coverage**:
```bash
# Install coverage
pip install pytest-cov

# Basic coverage
pytest --cov=src

# With missing lines
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Multiple formats
pytest --cov=src --cov-report=term --cov-report=html --cov-report=xml

# Specific module
pytest --cov=mypackage.mymodule tests/

# Fail under threshold
pytest --cov=src --cov-fail-under=70
```

**Configure in pyproject.toml**:
```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
    "*/venv/*"
]

[tool.coverage.report]
precision = 2
show_missing = true
skip_covered = false
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod"
]

[tool.coverage.html]
directory = "htmlcov"
```

**Using coverage.py directly**:
```bash
# Run tests with coverage
coverage run -m pytest

# Generate report
coverage report

# Show missing lines
coverage report --show-missing

# HTML report
coverage html
open htmlcov/index.html

# Erase previous data
coverage erase
```

### Ruby (SimpleCov)

**Setup in test_helper.rb or spec_helper.rb**:
```ruby
require 'simplecov'

SimpleCov.start do
  add_filter '/test/'
  add_filter '/spec/'
  add_filter '/vendor/'

  add_group 'Models', 'app/models'
  add_group 'Controllers', 'app/controllers'
  add_group 'Helpers', 'app/helpers'
  add_group 'Libraries', 'lib'

  minimum_coverage 70
  minimum_coverage_by_file 50
end
```

**Run Coverage**:
```bash
# Run tests (coverage automatic with SimpleCov)
bundle exec rspec

# Run with specific formatter
COVERAGE=true bundle exec rspec

# View HTML report
open coverage/index.html
```

### Go

**Run Coverage**:
```bash
# Basic coverage
go test -cover ./...

# Detailed coverage
go test -coverprofile=coverage.out ./...

# View coverage report
go tool cover -func=coverage.out

# HTML report
go tool cover -html=coverage.out -o coverage.html
open coverage.html

# Coverage for specific package
go test -cover ./pkg/mypackage

# Fail on low coverage (using script)
go test -coverprofile=coverage.out ./...
go tool cover -func=coverage.out | grep total | awk '{if ($3+0 < 70) exit 1}'
```

### Java (JaCoCo)

**Maven Configuration (pom.xml)**:
```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.8</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
        <execution>
            <id>jacoco-check</id>
            <goals>
                <goal>check</goal>
            </goals>
            <configuration>
                <rules>
                    <rule>
                        <element>PACKAGE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.70</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
</plugin>
```

**Run Coverage**:
```bash
# Maven
mvn clean test
mvn jacoco:report
open target/site/jacoco/index.html

# Gradle
./gradlew test jacocoTestReport
open build/reports/jacoco/test/html/index.html
```

### C# (.NET)

**Run Coverage**:
```bash
# Using coverlet
dotnet test /p:CollectCoverage=true

# With output formats
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=lcov

# HTML report (requires ReportGenerator)
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=cobertura
dotnet tool install -g dotnet-reportgenerator-globaltool
reportgenerator -reports:coverage.cobertura.xml -targetdir:coverage-report
open coverage-report/index.html

# Threshold
dotnet test /p:CollectCoverage=true /p:Threshold=70
```

### PHP (PHPUnit)

**Run Coverage**:
```bash
# Basic coverage (requires Xdebug or pcov)
phpunit --coverage-text

# HTML report
phpunit --coverage-html coverage
open coverage/index.html

# Clover XML
phpunit --coverage-clover coverage.xml

# With filter
phpunit --coverage-text --filter MyTestClass
```

**Configure in phpunit.xml**:
```xml
<phpunit>
    <coverage>
        <include>
            <directory suffix=".php">src</directory>
        </include>
        <exclude>
            <directory>tests</directory>
            <directory>vendor</directory>
        </exclude>
        <report>
            <html outputDirectory="coverage/html"/>
            <clover outputFile="coverage/clover.xml"/>
            <text outputFile="php://stdout" showUncoveredFiles="true"/>
        </report>
    </coverage>
</phpunit>
```

## Interpreting Coverage Reports

### Coverage Metrics Explained

**Line Coverage**:
- **Meaning**: Percentage of lines executed during tests
- **Example**: 70% means 70 out of 100 lines were executed
- **Good Target**: 70-80%+

**Branch Coverage**:
- **Meaning**: Percentage of conditional branches taken
- **Example**: `if (x > 0)` has two branches (true/false)
- **Good Target**: 70-80%+
- **Why Important**: Tests both success and failure paths

**Function Coverage**:
- **Meaning**: Percentage of functions/methods called
- **Example**: 10 out of 12 functions executed = 83%
- **Good Target**: 80-90%+

**Statement Coverage**:
- **Meaning**: Percentage of statements executed
- **Example**: Similar to line coverage but counts statements
- **Good Target**: 70-80%+

### Reading Coverage Output

**Example Coverage Report**:
```
--------------------|---------|----------|---------|---------|-------------------
File                | % Stmts | % Branch | % Funcs | % Lines | Uncovered Line #s
--------------------|---------|----------|---------|---------|-------------------
All files           |   73.45 |    68.23 |   75.12 |   73.28 |
 src/               |   78.92 |    72.45 |   80.00 |   78.75 |
  api.js            |   85.23 |    80.00 |   88.89 |   85.00 | 45-48,67
  auth.js           |   92.31 |    87.50 |  100.00 |   92.31 | 23,56
  utils.js          |   65.22 |    58.33 |   70.00 |   65.00 | 12,34-45,78-89
 src/models/        |   45.67 |    38.89 |   50.00 |   45.50 |
  user.js           |   48.15 |    40.00 |   55.56 |   48.00 | 23-67,89-123
  post.js           |   42.86 |    37.50 |   44.44 |   42.50 | 12-45,67-89,102-156
--------------------|---------|----------|---------|---------|-------------------
```

**Analyzing the Report**:
1. **Overall Coverage (73.45%)**: Approaching target, needs improvement
2. **High Coverage (api.js, auth.js)**: Well-tested, maintain this
3. **Low Coverage (src/models/)**: Priority area for new tests
4. **Uncovered Lines**: Specific lines needing test coverage

### Finding Uncovered Code

**Using Coverage Reports**:
```bash
# Show uncovered lines
pytest --cov=src --cov-report=term-missing

# Generate HTML report
npm test -- --coverage
open coverage/index.html

# Find files below threshold
npm test -- --coverage | grep -E '[0-9]+\.[0-9]+\s+\|\s+[0-6][0-9]\.'
```

**Identify Priority Areas**:
1. **Critical business logic**: Payment, authentication, data validation
2. **Low coverage**: Files below 50%
3. **High complexity**: Complex functions with low coverage
4. **Recent changes**: New code without tests
5. **Bug-prone areas**: Code with history of bugs

## Coverage in CI/CD

### GitHub Actions

**Example Workflow**:
```yaml
name: Test Coverage

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests with coverage
        run: npm test -- --coverage

      - name: Check coverage threshold
        run: |
          coverage=$(npm test -- --coverage --silent | grep "All files" | awk '{print $4}' | sed 's/%//')
          if (( $(echo "$coverage < 70" | bc -l) )); then
            echo "Coverage $coverage% is below 70%"
            exit 1
          fi

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/lcov.info
          flags: unittests
          fail_ci_if_error: true
```

### GitLab CI

**Example .gitlab-ci.yml**:
```yaml
test:coverage:
  stage: test
  script:
    - npm ci
    - npm test -- --coverage
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/cobertura-coverage.xml
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### Coverage Services

**Codecov**:
```bash
# Upload coverage
bash <(curl -s https://codecov.io/bash)

# Or using action (GitHub)
- uses: codecov/codecov-action@v3
  with:
    files: ./coverage/lcov.info
    flags: unittests
    name: codecov-umbrella
```

**Coveralls**:
```bash
# Install
npm install --save-dev coveralls

# Upload
cat ./coverage/lcov.info | npx coveralls

# Or in package.json
"scripts": {
  "coveralls": "npm test -- --coverage && cat ./coverage/lcov.info | coveralls"
}
```

## Best Practices

### Setting Coverage Targets

**Recommended Thresholds**:
- **New Projects**: Start at 70%, increase to 80%+
- **Legacy Projects**: Start at current%, increase by 5% per quarter
- **Critical Paths**: 90%+ (payment, auth, data validation)
- **Utilities**: 80%+ (helper functions, formatters)
- **UI Components**: 60-70% (harder to test, focus on logic)

### Coverage Doesn't Mean Quality

**Remember**:
- ✅ **Good**: 80% coverage with meaningful assertions
- ❌ **Bad**: 80% coverage with tests that don't assert anything
- ✅ **Good**: 60% coverage testing critical paths thoroughly
- ❌ **Bad**: 90% coverage missing edge cases

**Write Good Tests**:
```javascript
// ❌ Bad: High coverage, poor quality
test('user function', () => {
  createUser('test', 'test@example.com');
  // No assertions - test passes but doesn't verify anything
});

// ✅ Good: Tests actual behavior
test('createUser creates user with correct properties', () => {
  const user = createUser('John', 'john@example.com');
  expect(user.name).toBe('John');
  expect(user.email).toBe('john@example.com');
  expect(user.id).toBeDefined();
  expect(user.createdAt).toBeInstanceOf(Date);
});

// ✅ Good: Tests edge cases
test('createUser throws on invalid email', () => {
  expect(() => createUser('John', 'invalid-email'))
    .toThrow('Invalid email format');
});
```

### Focus on Critical Paths

**Prioritize Testing**:
1. **Authentication/Authorization** (90%+)
2. **Payment Processing** (95%+)
3. **Data Validation** (85%+)
4. **Business Logic** (80%+)
5. **API Endpoints** (80%+)
6. **Utility Functions** (75%+)
7. **UI Components** (60%+)

### Exclude Irrelevant Code

**What to Exclude**:
- Test files themselves
- Build configuration
- Generated code
- Type definitions
- Third-party code
- Development-only code

```javascript
// .coveragerc (Python)
[coverage:run]
omit =
    */tests/*
    */migrations/*
    */venv/*
    */__pycache__/*
    */node_modules/*

// jest.config.js
module.exports = {
  coveragePathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/coverage/',
    '.test.js$',
    '.spec.js$'
  ]
};
```

## Troubleshooting

### Coverage Not Generated

**Issue**: No coverage report after running tests

**Solutions**:
```bash
# Ensure coverage tool installed
npm install --save-dev jest  # or coverage tool

# Check test script
npm test -- --coverage --verbose

# Clear cache
npm test -- --clearCache
rm -rf coverage/

# Check configuration
cat jest.config.js
```

### Coverage Reports Incorrect

**Issue**: Coverage shows 0% or incorrect values

**Solutions**:
```bash
# Clear previous coverage
rm -rf coverage/ .nyc_output/

# Regenerate
npm test -- --coverage --no-cache

# Check source maps (TypeScript)
# Ensure tsconfig.json has:
{
  "compilerOptions": {
    "sourceMap": true,
    "inlineSourceMap": false
  }
}
```

### Slow Coverage Generation

**Issue**: Coverage takes too long

**Solutions**:
```bash
# Run in parallel
npm test -- --coverage --maxWorkers=4

# Only for changed files
npm test -- --coverage --onlyChanged

# Exclude unnecessary files
# Update coveragePathIgnorePatterns in config
```

## Integration with Other Skills

- **Testing**: Run coverage as part of test suite
- **Code Review**: Check coverage in PR reviews
- **CI/CD**: Enforce coverage thresholds
- **Documentation**: Document coverage targets
- **Git Workflow**: Include coverage in commit hooks

## Success Metrics

- **Coverage Percentage**: Target 70-80%+ maintained
- **Coverage Trend**: Increasing over time (not decreasing)
- **Critical Path Coverage**: 90%+ for high-risk code
- **Coverage in PRs**: New code includes tests
- **Time to Generate**: <2 minutes for full coverage
- **False Gaps**: Minimal uncovered but intentionally untested code

---

**Command Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
