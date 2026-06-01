# Documentation Writing Skill

**Category**: Development Skill
**Difficulty**: Beginner to Intermediate
**Prerequisites**: Understanding of project being documented
**Estimated Time**: 30 minutes - 4 hours depending on scope

---

## Overview

Documentation writing is the practice of creating clear, accurate, and useful documentation for software projects. Good documentation helps users understand how to use your software, helps developers contribute, and serves as a reference for your future self.

**Key Principles**:
- **Write for Your Audience**: Tailor content to reader's knowledge level
- **Show, Don't Just Tell**: Use examples and code snippets
- **Keep It Updated**: Documentation that's wrong is worse than no documentation
- **Make It Discoverable**: Organize logically, use clear headings
- **Be Concise**: Respect reader's time, get to the point

---

## When to Use This Skill

**Write documentation when**:
- ✅ Starting a new project (README, setup instructions)
- ✅ Adding a new feature (update docs)
- ✅ Changing an API (update API docs)
- ✅ Fixing a common issue (add to troubleshooting)
- ✅ Onboarding new team members (contributing guide)
- ✅ Releasing a new version (changelog, migration guide)
- ✅ Getting questions repeatedly (FAQ entry)
- ✅ Code review requests docs update

**Don't document when**:
- ❌ Code is still experimental/unstable
- ❌ Documentation would be obvious from code
- ❌ Writing it just to check a box

---

## Types of Documentation

### 1. README.md (Project Overview)

**Purpose**: First impression, quick start guide
**Audience**: New users, potential contributors
**Essential Sections**:

```markdown
# Project Name

Brief description (1-2 sentences)

## Features

- Feature 1
- Feature 2
- Feature 3

## Quick Start

\`\`\`bash
npm install project-name
npm start
\`\`\`

## Installation

Detailed installation instructions

## Usage

Basic usage examples with code

## Documentation

Link to full documentation

## Contributing

Link to CONTRIBUTING.md

## License

License information
```

**Best Practices**:
- Keep it concise (< 500 lines)
- Add screenshots/GIFs for visual projects
- Include badges (build status, coverage, version)
- Write for someone with zero context
- Test instructions on a fresh machine

### 2. API Documentation

**Purpose**: Describe how to use your API
**Audience**: Developers integrating with your API
**Formats**: OpenAPI/Swagger, JSDoc, docstrings

**Example (REST API)**:
```markdown
## GET /api/users/:id

Retrieve a user by ID.

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| id | string | Yes | User ID |

### Response

\`\`\`json
{
  "id": "123",
  "name": "John Doe",
  "email": "john@example.com",
  "created_at": "2025-01-01T00:00:00Z"
}
\`\`\`

### Errors

| Status | Description |
|--------|-------------|
| 404 | User not found |
| 500 | Server error |

### Example

\`\`\`bash
curl https://api.example.com/users/123
\`\`\`
```

**Best Practices**:
- Document all endpoints
- Show request and response examples
- List all parameters and their types
- Document error codes
- Include authentication requirements
- Keep in sync with code (use tools like Swagger)

### 3. User Guide / Tutorial

**Purpose**: Teach users how to accomplish specific tasks
**Audience**: End users, new users
**Format**: Step-by-step instructions

**Structure**:
```markdown
# How to [Accomplish Task]

**Goal**: [What user will learn]
**Prerequisites**: [What's needed before starting]
**Time**: [Estimated time]

## Step 1: [First Action]

Explanation of what and why.

\`\`\`bash
command-to-run
\`\`\`

**Expected output**:
\`\`\`
Output here
\`\`\`

## Step 2: [Next Action]

...

## Troubleshooting

**Problem**: [Common issue]
**Solution**: [How to fix]

## Next Steps

- Link to related guide
- Link to advanced topics
```

**Best Practices**:
- Start with the end goal
- Include screenshots where helpful
- Test every step yourself
- Anticipate common problems
- Link to related resources

### 4. Architecture Documentation

**Purpose**: Explain system design and decisions
**Audience**: Developers, future maintainers
**Sections**: Overview, components, data flow, decisions

**Example**:
```markdown
# Architecture

## Overview

[High-level description of the system]

## System Diagram

\`\`\`
┌─────────┐      ┌──────────┐      ┌──────────┐
│ Frontend│─────▶│    API   │─────▶│ Database │
└─────────┘      └──────────┘      └──────────┘
                       │
                       ▼
                  ┌─────────┐
                  │  Cache  │
                  └─────────┘
\`\`\`

## Components

### Frontend
- **Technology**: React + TypeScript
- **Responsibility**: User interface
- **Key Files**: src/components/*

### API
- **Technology**: Node.js + Express
- **Responsibility**: Business logic, data access
- **Key Files**: src/api/*

## Data Flow

1. User action triggers frontend event
2. Frontend makes API request
3. API checks cache
4. If cache miss, query database
5. Return response to frontend

## Key Decisions

### Why React instead of Vue?
- Team familiarity
- Larger ecosystem
- Better TypeScript support

## Related Documents

- [API Documentation](./api.md)
- [Database Schema](./database.md)
```

**Best Practices**:
- Use diagrams for complex systems
- Explain "why" not just "what"
- Document trade-offs and decisions
- Keep updated as architecture evolves

### 5. Code Comments

**Purpose**: Explain complex or non-obvious code
**Audience**: Future developers (including yourself)
**When to Use**: Complex logic, workarounds, important context

**Good Comments**:
```python
# Calculate compound interest using formula: A = P(1 + r/n)^(nt)
# where P=principal, r=rate, n=compounds per year, t=years
def calculate_compound_interest(principal, rate, years):
    return principal * (1 + rate / 12) ** (12 * years)

# HACK: API returns dates in inconsistent formats
# Sometimes "2025-01-01", sometimes "01/01/2025"
# This normalizes to ISO format
def normalize_date(date_string):
    # Try ISO format first
    try:
        return datetime.fromisoformat(date_string)
    except ValueError:
        # Fall back to MM/DD/YYYY
        return datetime.strptime(date_string, "%m/%d/%Y")

# TODO: Refactor this once we upgrade to Python 3.12
# Current implementation is a workaround for Python 3.8 limitation
```

**Bad Comments** (Don't do this):
```python
# Bad: States the obvious
# Increment counter by 1
counter += 1

# Bad: Outdated comment (code changed but comment didn't)
# Returns user email
def get_user_name(user_id):  # Actually returns name, not email!
    return user.name

# Bad: Comment instead of fixing code
# This is a bit hacky but it works
messy_complex_code_that_should_be_refactored()
```

**Best Practices**:
- Explain "why", not "what"
- Keep comments updated with code
- Use comments for non-obvious decisions
- Prefer self-documenting code over comments
- Use TODO, FIXME, HACK tags consistently

### 6. Changelog

**Purpose**: Track what changed in each version
**Audience**: Users, developers
**Format**: Keep a Changelog standard

**Example**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- New feature X

### Changed
- Improved performance of Y

### Fixed
- Bug in Z

## [1.2.0] - 2025-11-12

### Added
- User authentication system
- Email notifications

### Changed
- Updated UI design
- Improved error messages

### Deprecated
- Old API endpoint /v1/users (use /v2/users)

### Removed
- Legacy dashboard

### Fixed
- Login redirect bug (#123)
- Memory leak in cache (#456)

### Security
- Fixed XSS vulnerability in search

## [1.1.0] - 2025-10-01

...
```

**Best Practices**:
- Update with every release
- Group changes by type (Added, Changed, Fixed, etc.)
- Link to issue tracker
- Write for end users, not developers
- Include migration guides for breaking changes

---

## Documentation Writing Process

### Step 1: Identify What Needs Documentation

**Ask yourself**:
- What changed since last docs update?
- What questions do users ask?
- What confused you when you started?
- What would a new team member need to know?
- What APIs are public-facing?

### Step 2: Know Your Audience

**For End Users**:
- Assume no technical knowledge
- Focus on "how to do X"
- Use screenshots and examples
- Avoid jargon

**For Developers**:
- Assume technical knowledge
- Focus on "how it works"
- Include code examples
- Link to source code

**For Contributors**:
- Explain project structure
- Document development setup
- Describe contribution process
- Link to coding standards

### Step 3: Create an Outline

```markdown
# Document Title

## Introduction
- What this document covers
- Who should read this

## Prerequisites
- Required knowledge
- Required tools/setup

## Main Content
- Section 1
- Section 2
- Section 3

## Troubleshooting
- Common issues
- Solutions

## Next Steps
- Related docs
- Further reading
```

### Step 4: Write the First Draft

**Tips**:
- Write naturally, edit later
- Use active voice ("Run this command" not "This command should be run")
- Be specific ("Run `npm install`" not "Install dependencies somehow")
- Add examples early (code snippets, screenshots)
- Link liberally to related docs

### Step 5: Add Code Examples

**Good Example**:
```python
# Create a new user
user = User.create(
    name="John Doe",
    email="john@example.com",
    role="admin"
)

# Save to database
db.session.add(user)
db.session.commit()

print(f"Created user {user.name} with ID {user.id}")
# Output: Created user John Doe with ID 123
```

**Include**:
- Imports/setup needed
- Full working code, not fragments
- Expected output
- Error cases if relevant

### Step 6: Review and Edit

**Checklist**:
- [ ] Is it accurate? (Test all code examples)
- [ ] Is it clear? (No ambiguous language)
- [ ] Is it concise? (Remove fluff)
- [ ] Is it complete? (All steps included)
- [ ] Is it well-organized? (Logical flow)
- [ ] Are there enough examples?
- [ ] Are links working?
- [ ] Is spelling/grammar correct?

**Get feedback**:
- Ask someone unfamiliar with the project to follow docs
- Note where they get stuck
- Revise based on feedback

### Step 7: Keep It Updated

**When code changes, update docs**:
- Include docs in PR review checklist
- Run automated link checkers
- Review docs quarterly for accuracy
- Archive outdated docs, don't just delete

---

## Documentation Best Practices

### Writing Style

1. **Use Active Voice**
   - ✅ "Run the command"
   - ❌ "The command should be run"

2. **Be Specific**
   - ✅ "Install Python 3.8 or higher"
   - ❌ "Install a recent version of Python"

3. **Use Simple Language**
   - ✅ "This function returns the user's name"
   - ❌ "This function facilitates the acquisition of the nomenclature associated with the user entity"

4. **One Idea Per Sentence**
   - ✅ "Install the package. Then run the setup script."
   - ❌ "Install the package and then you should run the setup script which will configure everything."

5. **Use Lists and Tables**
   - Makes information scannable
   - Easier to read than paragraphs

### Formatting

1. **Use Headings Hierarchically**
   ```markdown
   # Main Title (H1)
   ## Section (H2)
   ### Subsection (H3)
   ```

2. **Format Code Properly**
   ```markdown
   Inline code: `variable_name`

   Code blocks:
   \`\`\`python
   def hello():
       print("Hello")
   \`\`\`
   ```

3. **Use Tables for Structured Data**
   ```markdown
   | Parameter | Type | Required |
   |-----------|------|----------|
   | id | string | Yes |
   | name | string | No |
   ```

4. **Add Visual Hierarchy**
   - Bold for emphasis: **important**
   - Italics for terms: *parameter*
   - Code formatting for: `technical_terms`

---

## Documentation Tools

### Generators
- **Sphinx** (Python): Generate docs from docstrings
- **JSDoc** (JavaScript): Generate API docs
- **Doxygen** (C++): Code documentation
- **MkDocs**: Static site from Markdown
- **Docusaurus**: React-based documentation sites

### Linters
- **markdownlint**: Check Markdown formatting
- **write-good**: Prose linter
- **alex**: Catch insensitive writing

### Hosting
- **GitHub Pages**: Free static hosting
- **Read the Docs**: Documentation hosting
- **GitBook**: Documentation platform
- **Docusaurus**: Self-hosted docs

---

## Example Documentation Session

```
PROJECT: REST API for E-commerce
TASK: Document new /api/products endpoint
TIME: 1 hour

Step 1: Outline
- Endpoint purpose
- Authentication required
- Request format
- Response format
- Error codes
- Example

Step 2: Write Draft (20 min)
[Wrote initial version with all sections]

Step 3: Add Code Examples (20 min)
- curl example
- JavaScript fetch example
- Response JSON example

Step 4: Review (15 min)
- Tested curl example
- Fixed typo in endpoint URL
- Added note about rate limiting

Step 5: Update (5 min)
- Added to API.md
- Updated changelog
- Linked from README

Result: Complete API documentation for new endpoint ✅
```

---

## Documentation Checklist

### New Project
- [ ] README.md with quick start
- [ ] Installation instructions
- [ ] Basic usage examples
- [ ] Link to full documentation
- [ ] CONTRIBUTING.md
- [ ] LICENSE file
- [ ] CODE_OF_CONDUCT.md (if public)

### New Feature
- [ ] Update README if user-facing
- [ ] Add API documentation
- [ ] Add code examples
- [ ] Update changelog
- [ ] Add inline comments for complex code
- [ ] Update architecture docs if needed

### Bug Fix
- [ ] Update changelog
- [ ] Add to troubleshooting section if relevant
- [ ] Update affected documentation

### Breaking Change
- [ ] Update changelog (mark as BREAKING)
- [ ] Write migration guide
- [ ] Update all affected docs
- [ ] Add deprecation notices

---

## Related Skills

- **Code Review**: Review documentation in PRs
- **Testing**: Test all code examples
- **Refactoring**: Improve docs structure

---

## Next Steps

After writing documentation:
1. Share with team for review
2. Test all code examples
3. Set up automated link checking
4. Schedule regular docs review
5. Add docs to PR checklist

---

*Documentation Writing Skill - Proto Gear v0.10.0*
*Generated: {{DATE}}*
