# /generate-changelog

> Generate or update CHANGELOG.md from git history

## Invocation Syntax

```
/generate-changelog [--since VERSION] [--output FILE] [--format FORMAT]
```

## Arguments

| Argument | Required | Type | Default | Description |
|----------|----------|------|---------|-------------|
| `--since` | No | string | last tag | Version to start from |
| `--output` | No | string | CHANGELOG.md | Output file path |
| `--format` | No | enum | keepachangelog | Format: keepachangelog, conventional, github |

## Examples

```
/generate-changelog
/generate-changelog --since v1.0.0
/generate-changelog --output docs/CHANGES.md
/generate-changelog --format conventional
/generate-changelog --since v1.2.0 --format github
```

---

## AI Execution Steps

> **For AI Agents**: Execute these steps when `/generate-changelog` is invoked.

### Step 1: Parse Arguments

Extract from user input:
- **--since**: Version tag to start from (default: detect last tag)
- **--output**: Output file path (default: CHANGELOG.md)
- **--format**: Format style (default: keepachangelog)

### Step 2: Get Git History

Read commits since the specified version:

```bash
# Get last tag if --since not specified
git describe --tags --abbrev=0

# Get commits since tag
git log {since_tag}..HEAD --pretty=format:"%h %s" --reverse
```

### Step 3: Categorize Commits

Group commits by type based on conventional commit prefixes:

| Prefix | Category |
|--------|----------|
| `feat:` | Added |
| `fix:` | Fixed |
| `docs:` | Documentation |
| `perf:` | Performance |
| `refactor:` | Changed |
| `BREAKING CHANGE:` | Breaking |
| `security:` | Security |
| `deprecate:` | Deprecated |

### Step 4: Generate Changelog Content

Format according to --format:

**Keep a Changelog (default)**:
```markdown
## [Unreleased]

### Added
- {feat commits}

### Changed
- {refactor commits}

### Fixed
- {fix commits}

### Security
- {security commits}
```

**Conventional**:
```markdown
## {version} ({date})

### Features
- {feat commits with scope}

### Bug Fixes
- {fix commits with scope}
```

### Step 5: Write or Update File

- If file exists: Prepend new section after header
- If file doesn't exist: Create with full template

### Step 6: Confirm to User

```
Changelog updated: {output_file}
- Added: {count} new entries
- From: {since_tag} to HEAD
- Format: {format}
```

---

## Completion Criteria

- [ ] Git history retrieved successfully
- [ ] Commits categorized by type
- [ ] Changelog content generated in correct format
- [ ] File written or updated
- [ ] User notified of changes

---

## Error Handling

| Condition | Error Message |
|-----------|---------------|
| Not a git repository | "Error: Not a git repository. Initialize with `git init` first." |
| No commits found | "Error: No commits found since {version}." |
| Invalid --since tag | "Error: Tag '{tag}' not found. Use `git tag` to list available tags." |
| Invalid --format | "Error: Invalid format '{value}'. Must be: keepachangelog, conventional, github" |
| Write permission denied | "Error: Cannot write to {output}. Check file permissions." |

---

## Format Reference

The sections below provide detailed changelog format guidelines and automation tools.

---

## When to Use This Command

Use this command when you need to:

- **Version Release**: Document changes before releasing a new version
- **Create First Changelog**: Set up changelog for existing project
- **Update Changelog**: Add recent changes to CHANGELOG.md
- **Automate Changelog**: Set up automated changelog generation
- **Format Changelog**: Follow standard changelog conventions
- **Generate Release Notes**: Create GitHub/GitLab release notes
- **Communicate Changes**: Keep users informed of updates

## Quick Reference

### Manual Changelog (Keep a Changelog Format)

**CHANGELOG.md Structure**:
```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- New feature description

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Now removed features

### Fixed
- Bug fixes

### Security
- Vulnerability fixes

## [1.2.0] - 2024-01-15

### Added
- Real-time notifications using WebSockets
- Dark mode support for user interface
- Export data to CSV functionality
- User profile customization options

### Changed
- Improved performance of database queries (30% faster)
- Updated authentication flow for better UX
- Redesigned dashboard layout
- Upgraded to Node.js 18 (from 16)

### Deprecated
- API v1 endpoints (use v2 instead)
- Legacy authentication method (remove in v2.0.0)

### Fixed
- Resolved memory leak in WebSocket connections
- Fixed pagination issue with large datasets
- Corrected timezone handling in date picker
- Addressed accessibility issues in forms

### Security
- Updated dependencies with known vulnerabilities
- Implemented rate limiting on authentication endpoints
- Enhanced input validation to prevent XSS attacks

## [1.1.0] - 2023-12-01

### Added
- User role management system
- API documentation with Swagger/OpenAPI
- Integration tests for critical paths

### Changed
- Migrated from REST to GraphQL for main API
- Updated UI framework to React 18

### Fixed
- Resolved race condition in async operations
- Fixed incorrect calculations in reports

## [1.0.0] - 2023-10-15

### Added
- Initial release
- User authentication and authorization
- CRUD operations for main resources
- RESTful API endpoints
- Responsive web interface
- Unit and integration test suite

[Unreleased]: https://github.com/org/repo/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/org/repo/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/org/repo/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/org/repo/releases/tag/v1.0.0
```

### Change Categories

**Added**: New features or functionality
```markdown
### Added
- User can now export data to PDF format
- Added real-time collaboration features
- New API endpoint `/api/v2/analytics`
```

**Changed**: Changes in existing functionality
```markdown
### Changed
- Improved search algorithm (3x faster)
- Updated default theme colors
- Changed pagination from offset to cursor-based
```

**Deprecated**: Features that will be removed soon
```markdown
### Deprecated
- `POST /api/v1/login` endpoint (use `/api/v2/auth/login` instead)
- `getUserData()` function (use `fetchUserProfile()` instead)
- Support for Internet Explorer 11 (removal in v2.0.0)
```

**Removed**: Features that have been removed
```markdown
### Removed
- Removed legacy API v1 endpoints
- Dropped support for Node.js 14
- Removed deprecated `oldMethod()` function
```

**Fixed**: Bug fixes
```markdown
### Fixed
- Fixed memory leak in image processing
- Resolved incorrect date formatting in reports
- Corrected calculation error in tax totals
```

**Security**: Security vulnerability fixes
```markdown
### Security
- Fixed SQL injection vulnerability in search
- Patched XSS vulnerability in user input
- Updated dependencies with CVE fixes (lodash, axios)
```

## Automated Changelog Generation

### From Conventional Commits

**Using standard-version**:
```bash
# Install
npm install --save-dev standard-version

# Add to package.json
{
  "scripts": {
    "release": "standard-version",
    "release:minor": "standard-version --release-as minor",
    "release:major": "standard-version --release-as major",
    "release:patch": "standard-version --release-as patch"
  }
}

# Generate changelog and bump version
npm run release

# First release
npm run release -- --first-release

# Dry run (preview changes)
npm run release -- --dry-run

# Custom configuration (.versionrc.json)
{
  "types": [
    {"type": "feat", "section": "Features"},
    {"type": "fix", "section": "Bug Fixes"},
    {"type": "docs", "section": "Documentation"},
    {"type": "style", "section": "Styles", "hidden": true},
    {"type": "refactor", "section": "Code Refactoring"},
    {"type": "perf", "section": "Performance Improvements"},
    {"type": "test", "section": "Tests", "hidden": true},
    {"type": "build", "section": "Build System"},
    {"type": "ci", "section": "CI/CD", "hidden": true}
  ],
  "commitUrlFormat": "{{host}}/{{owner}}/{{repository}}/commit/{{hash}}",
  "compareUrlFormat": "{{host}}/{{owner}}/{{repository}}/compare/{{previousTag}}...{{currentTag}}",
  "issueUrlFormat": "{{host}}/{{owner}}/{{repository}}/issues/{{id}}",
  "userUrlFormat": "{{host}}/{{user}}"
}
```

**Using conventional-changelog-cli**:
```bash
# Install
npm install --save-dev conventional-changelog-cli

# Generate changelog
npx conventional-changelog -p angular -i CHANGELOG.md -s

# First release (generate complete changelog)
npx conventional-changelog -p angular -i CHANGELOG.md -s -r 0

# Different commit convention
npx conventional-changelog -p atom -i CHANGELOG.md -s

# Add to package.json
{
  "scripts": {
    "changelog": "conventional-changelog -p angular -i CHANGELOG.md -s"
  }
}
```

**Using release-it**:
```bash
# Install
npm install --save-dev release-it @release-it/conventional-changelog

# Configure (.release-it.json)
{
  "git": {
    "commitMessage": "chore: release v${version}"
  },
  "github": {
    "release": true
  },
  "npm": {
    "publish": false
  },
  "plugins": {
    "@release-it/conventional-changelog": {
      "preset": "angular",
      "infile": "CHANGELOG.md"
    }
  }
}

# Run release
npx release-it

# Dry run
npx release-it --dry-run

# Add to package.json
{
  "scripts": {
    "release": "release-it"
  }
}
```

### From Git Commits

**Using git-changelog**:
```bash
# Install
npm install --global git-changelog

# Generate from git history
git-changelog -t false

# With specific tag range
git-changelog v1.0.0..v1.1.0

# Save to file
git-changelog -f CHANGELOG.md
```

**Using auto-changelog**:
```bash
# Install
npm install --global auto-changelog

# Generate changelog
auto-changelog

# Specific version range
auto-changelog --starting-version v1.0.0

# Custom template
auto-changelog --template custom-template.hbs

# Configure (package.json)
{
  "auto-changelog": {
    "output": "CHANGELOG.md",
    "template": "keepachangelog",
    "unreleased": true,
    "commitLimit": false,
    "includeBranch": ["main", "develop"]
  }
}
```

**Manual extraction from git log**:
```bash
# Get commits since last tag
git log $(git describe --tags --abbrev=0)..HEAD --oneline

# Group by type (requires conventional commits)
git log --oneline --no-merges | grep "^feat:" | sed 's/^feat: /- /'

# Generate commit list for specific version
git log v1.0.0..v1.1.0 --pretty=format:"- %s" --reverse

# Format with commit hash
git log --oneline --decorate --graph --since="2024-01-01"
```

### From GitHub/GitLab

**Using GitHub CLI (gh)**:
```bash
# Generate release notes
gh release create v1.2.0 --generate-notes

# Create release with custom notes
gh release create v1.2.0 \
  --title "Release v1.2.0" \
  --notes-file RELEASE_NOTES.md

# View release notes for existing release
gh release view v1.2.0

# List all releases
gh release list
```

**Using GitLab CI**:
```yaml
# .gitlab-ci.yml
release:
  stage: release
  image: registry.gitlab.com/gitlab-org/release-cli:latest
  script:
    - echo "Creating release $CI_COMMIT_TAG"
  release:
    tag_name: '$CI_COMMIT_TAG'
    description: './CHANGELOG.md'
  only:
    - tags
```

## Language-Specific Tools

### Python

**Using towncrier**:
```bash
# Install
pip install towncrier

# Configure (pyproject.toml)
[tool.towncrier]
package = "mypackage"
package_dir = "src"
filename = "CHANGELOG.md"
directory = "changelog/"
title_format = "## [{version}] - {project_date}"
issue_format = "[#{issue}](https://github.com/org/repo/issues/{issue})"

[[tool.towncrier.type]]
directory = "feature"
name = "Features"
showcontent = true

[[tool.towncrier.type]]
directory = "bugfix"
name = "Bug Fixes"
showcontent = true

[[tool.towncrier.type]]
directory = "doc"
name = "Documentation"
showcontent = true

# Create news fragment
echo "Added new feature X" > changelog/123.feature

# Build changelog
towncrier build --version 1.2.0

# Draft (don't modify files)
towncrier build --version 1.2.0 --draft
```

**Using python-semantic-release**:
```bash
# Install
pip install python-semantic-release

# Configure (setup.cfg or pyproject.toml)
[semantic_release]
version_variable = src/mypackage/__init__.py:__version__
version_source = tag
upload_to_pypi = false
upload_to_release = true
build_command = python -m build

# Run release
semantic-release publish

# Dry run
semantic-release publish --noop
```

### Ruby

**Using github_changelog_generator**:
```bash
# Install
gem install github_changelog_generator

# Generate changelog
github_changelog_generator

# With options
github_changelog_generator \
  --user myuser \
  --project myproject \
  --token YOUR_GITHUB_TOKEN \
  --since-tag v1.0.0

# Configure (.github_changelog_generator)
user=myuser
project=myproject
exclude-labels=duplicate,question,invalid,wontfix
```

### Go

**Using git-chglog**:
```bash
# Install
go install github.com/git-chglog/git-chglog/cmd/git-chglog@latest

# Initialize
git-chglog --init

# Generate changelog
git-chglog -o CHANGELOG.md

# Specific version
git-chglog -o CHANGELOG.md v1.0.0..v1.1.0

# Configure (.chglog/config.yml)
style: github
template: CHANGELOG.tpl.md
info:
  title: CHANGELOG
  repository_url: https://github.com/user/repo
options:
  commits:
    filters:
      Type:
        - feat
        - fix
        - perf
        - refactor
  commit_groups:
    title_maps:
      feat: Features
      fix: Bug Fixes
      perf: Performance Improvements
      refactor: Code Refactoring
```

## Semantic Versioning (SemVer)

### Version Number Format

**MAJOR.MINOR.PATCH** (e.g., 1.2.3)

**When to bump**:
- **MAJOR** (1.x.x → 2.0.0): Breaking changes, incompatible API changes
- **MINOR** (x.1.x → x.2.0): New features, backward-compatible
- **PATCH** (x.x.1 → x.x.2): Bug fixes, backward-compatible

**Examples**:
```markdown
## Breaking Change (Major: 1.5.2 → 2.0.0)
- Removed deprecated API v1 endpoints
- Changed authentication from API keys to JWT (breaking)
- Renamed main function `getData()` to `fetchData()`

## New Features (Minor: 1.5.2 → 1.6.0)
- Added real-time notifications feature
- New GraphQL API alongside existing REST API
- Added dark mode theme option

## Bug Fixes (Patch: 1.5.2 → 1.5.3)
- Fixed memory leak in image processing
- Corrected calculation error in tax totals
- Resolved race condition in async operations
```

### Pre-release Versions

**Format**: `1.0.0-alpha.1`, `1.0.0-beta.2`, `1.0.0-rc.1`

**Examples**:
```markdown
## [1.0.0-rc.1] - 2024-01-15 (Release Candidate)
- Final testing before 1.0.0 release
- Last chance for bug fixes

## [1.0.0-beta.2] - 2024-01-10 (Beta)
- Feature complete, testing phase
- Known issues being resolved

## [1.0.0-alpha.3] - 2024-01-05 (Alpha)
- Early preview, not feature complete
- For testing and feedback only
```

## Changelog Best Practices

### Writing Good Changelog Entries

**Good Examples**:
```markdown
✅ Good: Specific, describes impact
- Fixed memory leak in WebSocket connections that caused server crashes after 24 hours
- Added bulk export feature allowing users to download up to 10,000 records at once
- Improved search performance by 70% using indexed database queries

❌ Bad: Vague, no context
- Fixed bug
- Performance improvements
- Updated stuff
```

**User-Focused Language**:
```markdown
✅ Good: User perspective
- You can now export your data to PDF format
- The dashboard loads 3x faster
- Fixed an issue where uploaded images would sometimes fail to save

❌ Bad: Technical jargon
- Implemented PDF generation service
- Optimized SQL query execution
- Resolved S3 bucket permission error
```

### What to Include

**Include**:
- ✅ New features users can use
- ✅ Bug fixes that affect users
- ✅ Breaking changes with migration guide
- ✅ Security fixes (without exposing vulnerabilities)
- ✅ Deprecated features with timeline
- ✅ Performance improvements (if significant)

**Exclude**:
- ❌ Internal refactoring (unless user-facing impact)
- ❌ Dependency updates (unless security-related)
- ❌ Development tooling changes
- ❌ Code style changes
- ❌ Documentation-only updates (unless major)

### Organizing Entries

**Chronological Order** (newest first):
```markdown
## [Unreleased]
- Latest changes

## [1.2.0] - 2024-01-15
- Recent release

## [1.1.0] - 2023-12-01
- Older release

## [1.0.0] - 2023-10-15
- Initial release
```

**Group by Type** (within each version):
```markdown
## [1.2.0] - 2024-01-15

### Added (new features)
- Feature A
- Feature B

### Changed (modifications)
- Change A
- Change B

### Deprecated (soon removed)
- Old feature X

### Removed (now gone)
- Old feature Y

### Fixed (bugs)
- Bug fix A
- Bug fix B

### Security (vulnerabilities)
- Security patch A
```

## Changelog Automation in CI/CD

### GitHub Actions

**Automated Changelog on Release**:
```yaml
name: Generate Changelog

on:
  push:
    tags:
      - 'v*'

jobs:
  changelog:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Generate changelog
        run: |
          npx standard-version --skip.bump --skip.commit --skip.tag

      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          body_path: CHANGELOG.md
          draft: false
          prerelease: false

      - name: Commit changelog
        run: |
          git config user.name github-actions
          git config user.email github-actions@github.com
          git add CHANGELOG.md
          git commit -m "docs: update changelog for ${GITHUB_REF##*/}"
          git push
```

**Using release-drafter**:
```yaml
# .github/workflows/release-drafter.yml
name: Release Drafter

on:
  push:
    branches:
      - main

permissions:
  contents: write
  pull-requests: write

jobs:
  update_release_draft:
    runs-on: ubuntu-latest
    steps:
      - uses: release-drafter/release-drafter@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Configuration (.github/release-drafter.yml)**:
```yaml
name-template: 'v$RESOLVED_VERSION'
tag-template: 'v$RESOLVED_VERSION'
categories:
  - title: '🚀 Features'
    labels:
      - 'feature'
      - 'enhancement'
  - title: '🐛 Bug Fixes'
    labels:
      - 'fix'
      - 'bugfix'
      - 'bug'
  - title: '🧰 Maintenance'
    labels:
      - 'chore'
      - 'dependencies'
change-template: '- $TITLE @$AUTHOR (#$NUMBER)'
version-resolver:
  major:
    labels:
      - 'major'
      - 'breaking'
  minor:
    labels:
      - 'minor'
      - 'feature'
  patch:
    labels:
      - 'patch'
      - 'fix'
      - 'bugfix'
  default: patch
template: |
  ## What's Changed

  $CHANGES
```

### GitLab CI

**Automated Changelog**:
```yaml
# .gitlab-ci.yml
generate-changelog:
  stage: deploy
  image: node:18
  script:
    - npm ci
    - npx conventional-changelog -p angular -i CHANGELOG.md -s -r 0
    - git config user.name "GitLab CI"
    - git config user.email "ci@gitlab.com"
    - git add CHANGELOG.md
    - git commit -m "docs: update changelog [skip ci]"
    - git push https://oauth2:${CI_JOB_TOKEN}@${CI_SERVER_HOST}/${CI_PROJECT_PATH}.git HEAD:${CI_COMMIT_REF_NAME}
  only:
    - tags
```

## Integrations

### Link to Issues and PRs

**GitHub**:
```markdown
- Fixed authentication bug (#123)
- Added dark mode (PR #456)
- Resolves #789

[#123]: https://github.com/org/repo/issues/123
[PR #456]: https://github.com/org/repo/pull/456
```

**GitLab**:
```markdown
- Fixed authentication bug (!45)
- Added dark mode (MR !67)
- Closes #89
```

**Jira**:
```markdown
- Implemented user dashboard (PROJ-123)
- Fixed payment processing (PROJ-456)
```

### Attribution

**Thank Contributors**:
```markdown
### Added
- Real-time notifications (@username, #123)
- PDF export feature (Thanks to @contributor!)

### Fixed
- Memory leak in background worker (@developer, #456)

## Contributors

Thanks to these amazing people for contributing to v1.2.0:
- @alice - Feature development
- @bob - Bug fixes
- @charlie - Documentation improvements
```

## Tools Comparison

| Tool | Language | Auto/Manual | Conventional Commits | Semver |
|------|----------|-------------|---------------------|--------|
| standard-version | Node.js | Auto | Yes | Yes |
| conventional-changelog | Node.js | Auto | Yes | No |
| release-it | Node.js | Auto | Yes | Yes |
| auto-changelog | Node.js | Auto | No | No |
| towncrier | Python | Manual | No | No |
| git-chglog | Go | Auto | Yes | Yes |
| github-changelog-generator | Ruby | Auto | No | No |
| Manual (Keep a Changelog) | Any | Manual | No | Yes |

## Success Metrics

- **Changelog Completeness**: All releases documented
- **Update Frequency**: Updated with every release
- **User Comprehension**: Users understand changes
- **Time to Generate**: <5 minutes per release
- **Format Consistency**: Follows standard format
- **Link Validity**: All issue/PR links work
- **Community Engagement**: Contributors acknowledged

---

**Command Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
