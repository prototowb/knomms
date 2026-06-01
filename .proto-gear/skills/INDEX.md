# Skills Index

> **Implicit, continuous expertise** - Skills are activated automatically when contextually relevant

## Skills vs Slash Commands

| Aspect | Skills | Slash Commands |
|--------|--------|----------------|
| **Invocation** | Implicit (AI decides) | Explicit (`/command-name`) |
| **Nature** | Continuous expertise | Discrete action |
| **Duration** | Throughout task | Start → Finish |
| **Example** | "testing" skill during TDD | `/create-ticket "Add auth"` |

**Key insight**: Skills are **expertise you apply based on context**. They don't have a `/` prefix and aren't explicitly invoked by the user.

---

<!-- proto-gear:capability-index begin -->

## Available Skills (7)

_Auto-generated from `metadata.yaml`. Hand-edits inside this block are overwritten by `pg sync-indexes`._

### Code Review Best Practices

- **ID**: `skills/code-review`
- **File**: `code-review/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: quality
- **Description**: Systematic code review methodology for maintaining code quality and knowledge sharing
- **Tags**: code-review, quality, feedback, collaboration, best-practices, pull-request
- **Triggers**: "code review", "pull request", "pr review", "review code", "feedback", "quality check"
- **Contexts**: Before merging pull requests; After feature completion; During collaboration; When maintaining code quality
- **Dependencies**: optional: `skills/testing`, `workflows/feature-development`; suggested: `skills/security`, `skills/performance`
- **Agent roles**: Code Review Agent, Quality Assurance Agent, Senior Developer Agent, Full-Stack Developer Agent, Team Lead Agent

### Debugging & Troubleshooting

- **ID**: `skills/debugging`
- **File**: `debugging/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: debugging
- **Description**: Systematic debugging methodology for identifying and fixing software issues
- **Tags**: debugging, troubleshooting, problem-solving, root-cause-analysis, investigation
- **Triggers**: "debug", "troubleshoot", "bug", "error", "issue", "failing", "broken", "not working"
- **Contexts**: When code behaves unexpectedly; When tests fail; When errors occur; After bug reports; During investigation
- **Dependencies**: optional: `skills/testing`, `workflows/bug-fix`; suggested: `skills/code-review`, `commands/analyze-coverage`
- **Agent roles**: Debugging Agent, Bug Fix Agent, Troubleshooting Specialist, Full-Stack Developer Agent, Backend Agent, Frontend Agent

### Technical Documentation

- **ID**: `skills/documentation`
- **File**: `documentation/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: documentation
- **Description**: Writing clear, maintainable technical documentation for code and projects
- **Tags**: documentation, writing, clarity, maintenance, technical-writing, readme
- **Triggers**: "documentation", "docs", "readme", "write docs", "document code", "api documentation"
- **Contexts**: After implementing features; When onboarding new team members; Before releases; When APIs change
- **Dependencies**: optional: `workflows/documentation-update`; suggested: `skills/code-review`
- **Agent roles**: Documentation Agent, Technical Writer Agent, Full-Stack Developer Agent, Team Lead Agent

### Performance Optimization

- **ID**: `skills/performance`
- **File**: `performance/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: performance
- **Description**: Systematic performance optimization and profiling techniques
- **Tags**: performance, optimization, profiling, benchmarking, scalability, efficiency
- **Triggers**: "performance", "optimize", "slow", "profiling", "benchmark", "scalability", "efficiency"
- **Contexts**: When application is slow; Before production deployment; After feature implementation; When scaling systems
- **Dependencies**: optional: `skills/testing`, `skills/debugging`; suggested: `commands/analyze-coverage`, `workflows/feature-development`
- **Agent roles**: Performance Agent, Optimization Specialist, Backend Agent, Full-Stack Developer Agent, Database Specialist

### Code Refactoring

- **ID**: `skills/refactoring`
- **File**: `refactoring/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: refactoring
- **Description**: Systematic code refactoring techniques for improving code quality without changing behavior
- **Tags**: refactoring, code-quality, maintainability, clean-code, restructuring, improvement
- **Triggers**: "refactor", "clean up", "improve code", "code smell", "technical debt", "restructure"
- **Contexts**: When code is hard to understand; After feature implementation; Before adding new features; When addressing technical debt
- **Dependencies**: required: `skills/testing`; optional: `skills/code-review`; suggested: `workflows/refactoring`
- **Agent roles**: Refactoring Agent, Code Quality Agent, Full-Stack Developer Agent, Senior Developer Agent

### Security Best Practices

- **ID**: `skills/security`
- **File**: `security/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: security
- **Description**: Security best practices and vulnerability prevention techniques
- **Tags**: security, vulnerability, best-practices, owasp, authentication, authorization, encryption
- **Triggers**: "security", "vulnerability", "authentication", "authorization", "encryption", "owasp", "secure"
- **Contexts**: When handling user data; Before production deployment; After security audits; When implementing authentication
- **Dependencies**: optional: `skills/code-review`, `skills/testing`; suggested: `workflows/feature-development`
- **Agent roles**: Security Agent, Security Specialist, Backend Agent, Full-Stack Developer Agent, DevOps Agent

### Test-Driven Development

- **ID**: `skills/testing`
- **File**: `testing/SKILL.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: testing
- **Description**: TDD methodology with red-green-refactor cycle for quality code
- **Tags**: testing, tdd, quality, red-green-refactor, coverage, unit-tests, integration-tests
- **Triggers**: "write tests", "testing", "test coverage", "tdd", "quality assurance", "unit test", "integration test", "red green refactor"
- **Contexts**: Before implementing features; Fixing bugs (write test first); Refactoring code (maintain test coverage); Building critical business logic; Working on code with complex requirements
- **Dependencies**: optional: `workflows/feature-development`, `workflows/bug-fix`; suggested: `skills/debugging`, `skills/code-review`, `commands/analyze-coverage`
- **Agent roles**: Testing Agent, Quality Assurance Agent, Full-Stack Developer Agent, Backend Agent, Frontend Agent, TDD Specialist Agent

<!-- proto-gear:capability-index end -->

---

## How to Use Skills

Skills are **implicit expertise** - you don't invoke them with `/`, you activate them based on context.

### For AI Agents

**Skills are NOT slash commands!** There is no `/testing` or `/debugging` command. Instead:

1. **Recognize context** - Is the current task related to testing, debugging, code review, etc.?
2. **Load relevant skill** - Read the SKILL.md file for expertise
3. **Apply continuously** - Use the skill's patterns throughout your work
4. **No explicit invocation** - Skills are active when relevant, not triggered by user command

### When to Activate Skills

- **Testing skill**: When writing tests, implementing features with TDD, fixing bugs
- **Debugging skill**: When investigating errors, troubleshooting issues
- **Code Review skill**: When reviewing PRs, checking code quality
- **Refactoring skill**: When improving code structure

### Skill Structure

Each skill contains:
- **SKILL.md** - Main skill definition with philosophy and overview
- **patterns/** - Detailed sub-patterns for specific scenarios
- **examples/** - Concrete demonstrations of skill application

### Example: Using the Testing Skill

```
Task: Implement a new user authentication feature

1. Read skills/testing/SKILL.md
2. Learn the Red-Green-Refactor cycle
3. Read patterns/unit-testing.md for detailed guidance
4. Write failing test first
5. Implement minimal code to pass
6. Refactor while keeping tests green
```

---

## Adding Custom Skills

To add a new skill to this project:

1. Create directory: `skills/your-skill-name/`
2. Create `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: "Your Skill Name"
   type: "skill"
   version: "1.0.0"
   description: "Brief description"
   tags: ["keyword1", "keyword2"]
   category: "your-category"
   relevance:
     - trigger: "keywords that suggest this skill"
     - context: "when to use this skill"
   status: "stable"
   ---
   ```
3. Write detailed content with patterns and examples
4. Update this INDEX.md to list your new skill

---

*Proto Gear Skills Index*
