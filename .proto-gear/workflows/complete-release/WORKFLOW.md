# Complete Release Workflow

## Overview

This is the **complete end-to-end release workflow** for Proto Gear, documenting the exact process followed for v0.6.4 and all subsequent releases. It includes feature branch workflow, PR creation, version bumping, CHANGELOG updates, GitHub release creation, cleanup, branch syncing, and handoff preparation for the next agent.

**Key Principles**:
- ✅ Always use feature branches (never commit directly to main)
- ✅ Always create PRs for review
- ✅ Always use `gh` CLI for GitHub operations
- ✅ Always clean up branches after merge
- ✅ Always sync development with main after release
- ✅ Always prepare handoff documentation

---

## Prerequisites

Before starting:
- ✅ `gh` CLI installed (`winget install GitHub.cli` on Windows)
- ✅ `gh` authenticated (`gh auth login`)
- ✅ Feature work completed and tested
- ✅ All tests passing locally
- ✅ Clean working directory

---

## Release Types (Semantic Versioning)

### Patch Release (x.y.Z) - Most Common
- Bug fixes
- Test improvements
- Documentation updates
- Performance improvements
- Example: `v0.6.3` → `v0.6.4`

### Minor Release (x.Y.0)
- New features (backward compatible)
- New capabilities
- Enhancements
- Example: `v0.6.4` → `v0.7.0`

### Major Release (X.0.0)
- Breaking changes
- Major architecture changes
- API redesign
- Example: `v0.6.4` → `v1.0.0`

---

## Step 1: Create Feature Branch

**Start**: Always branch from `main` for release work

**Commands**:
```bash
# Ensure on main and up to date
git checkout main
git pull origin main

# Create feature branch
git checkout -b test/PROTO-XXX-description
# or
git checkout -b feat/PROTO-XXX-description
# or
git checkout -b fix/PROTO-XXX-description

# Verify branch name
git branch --show-current
```

**Branch Naming Convention**:
- Test improvements: `test/PROTO-XXX-description`
- New features: `feat/PROTO-XXX-description`
- Bug fixes: `fix/PROTO-XXX-description`
- Documentation: `docs/PROTO-XXX-description`

**Example** (v0.6.4):
```bash
git checkout main
git pull origin main
git checkout -b test/PROTO-017-improve-test-coverage
```

---

## Step 2: Complete Feature Work

**Do your work**:
- Write code
- Add tests
- Update documentation
- Ensure all tests pass

**Test thoroughly**:
```bash
# Run full test suite
pytest --cov=core --cov-report=term-missing

# Verify command works
pg init --dry-run

# Check code quality
python -m flake8 core/
```

**Commit as you go**:
```bash
git add <files>
git commit -m "type(scope): description

Details about the change

Closes PROTO-XXX"
```

**Example** (v0.6.4):
```bash
# Multiple commits during development
git commit -m "test: add comprehensive security tests"
git commit -m "test: add git workflow detection tests"
git commit -m "test: remove redundant UI tests"
```

---

## Step 3: Push Branch and Create PR

**Push feature branch**:
```bash
# First push - set upstream
git push -u origin test/PROTO-XXX-description
```

**Create PR using gh CLI**:
```bash
# Navigate to project directory
cd /path/to/proto-gear

# Create PR with gh CLI
gh pr create \
  --base main \
  --title "type(scope): description" \
  --body "## Summary

- Bullet point summary of changes
- What was done
- Why it was done

## Testing

- [x] All tests passing (XXX passed)
- [x] Coverage improved (XX% → YY%)
- [x] Manual testing completed

## Changes

**Added**:
- New feature/test/capability

**Changed**:
- Modified behavior

**Fixed**:
- Bug fix

Closes PROTO-XXX"
```

**Example** (v0.6.4):
```bash
gh pr create \
  --base main \
  --title "test(coverage): improve test coverage to 42%" \
  --body "## Summary

- Add 4 new comprehensive test files (73 tests)
- Remove 1,207 lines of redundant test code
- Achieve 42% overall coverage (up from 39%)
- Fix memory leaks and hanging tests

## Testing

- [x] 218 tests passing in 4.63 seconds
- [x] Zero memory leaks
- [x] Zero hanging tests

Closes PROTO-017"
```

---

## Step 4: Review and Merge PR

**Self-review** (if you're the only contributor):
```bash
# View PR in browser
gh pr view --web

# Check diff
gh pr diff

# Run tests one final time
pytest
```

**Merge PR**:
```bash
# Merge via gh CLI
gh pr merge --merge --delete-branch

# Or merge manually
git checkout main
git pull origin main
git merge test/PROTO-XXX-description --no-ff
git push origin main
git branch -d test/PROTO-XXX-description
git push origin --delete test/PROTO-XXX-description
```

**Verify merge**:
```bash
git log --oneline -5
```

---

## Step 5: Bump Version Numbers

**CRITICAL**: Update version in EXACTLY TWO files

**File 1: `pyproject.toml`**:
```bash
# Edit version line
version = "X.Y.Z"  # Old version
version = "X.Y.Z+1"  # New version
```

**File 2: `core/proto_gear_pkg/__init__.py`**:
```python
__version__ = "X.Y.Z"  # Old version
__version__ = "X.Y.Z+1"  # New version
```

**Example** (v0.6.4):
```bash
# In pyproject.toml
version = "0.6.3"  # Change to
version = "0.6.4"

# In core/proto_gear_pkg/__init__.py
__version__ = "0.6.3"  # Change to
__version__ = "0.6.4"
```

**Commit version bump**:
```bash
git add pyproject.toml core/proto_gear_pkg/__init__.py
git commit -m "chore(release): bump version to vX.Y.Z

Brief description of release contents

Closes PROTO-XXX"
git push origin main
```

---

## Step 6: Update CHANGELOG.md

**Add new version section at TOP of CHANGELOG.md**:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Changed
- Major changes and improvements

### Added
- New features, files, capabilities

### Fixed
- Bug fixes and corrections

### Technical
- Technical implementation details
```

**Example** (v0.6.4):
```markdown
## [0.6.4] - 2025-11-14

### Changed
- **Test Suite Overhaul** (PROTO-017)
  - Overall coverage: 39% → 42% (+3%)
  - proto_gear.py coverage: 52% → 61% (+9%)
  - 218 tests passing in 4.63 seconds
  - Zero memory leaks (fixed 20+ GB RAM consumption issue)
  - Zero hanging tests (fixed infinite wait on interactive input)
  - Removed 1,207 lines of redundant test code
  - Added 1,747 lines of targeted, high-value tests

### Added
- **New Test Files**
  - `test_capability_security.py` (19 tests)
  - `test_coverage_boost.py` (22 tests)
  - `test_project_detection.py` (15 tests)
  - `test_setup_function.py` (16 tests)

### Fixed
- **Memory leak in test suite** - Tests no longer hang
- **Test reliability** - All 218 tests pass consistently

### Technical
- Comprehensive git workflow testing
- Framework detection coverage for all major frameworks
- Security testing for symlink rejection, path traversal prevention
```

**Commit CHANGELOG**:
```bash
git add CHANGELOG.md
git commit -m "docs(changelog): add vX.Y.Z release notes

Brief summary of changes"
git push origin main
```

---

## Step 7: Create Git Tag

**Create annotated tag with full release notes**:

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - Title

## Key Changes

- Change 1
- Change 2
- Change 3

## Improvements

- Improvement 1
- Improvement 2

## Fixes

- Fix 1
- Fix 2

Closes PROTO-XXX"
```

**Example** (v0.6.4):
```bash
git tag -a v0.6.4 -m "Release v0.6.4 - Test Coverage Improvements

## Test Suite Enhancements

### Coverage Improvements
- Overall coverage: 39% → 42% (+3%)
- proto_gear.py coverage: 52% → 61% (+9%)
- 218 tests passing in 4.63 seconds

### New Test Files
- test_capability_security.py (19 tests)
- test_coverage_boost.py (22 tests)
- test_project_detection.py (15 tests)
- test_setup_function.py (16 tests)

### Quality Improvements
- Zero memory leaks (fixed 20+ GB RAM issue)
- Zero hanging tests (fixed infinite wait issue)

Closes PROTO-017"
```

**Push tag to remote**:
```bash
git push origin vX.Y.Z
```

---

## Step 8: Create GitHub Release with gh CLI

**CRITICAL**: Always use `gh` CLI for GitHub releases (part of our workflow)

**Install gh CLI** (if not already installed):
```bash
# Windows
winget install GitHub.cli

# Verify installation
gh --version
```

**Create GitHub release**:
```bash
gh release create vX.Y.Z \
  --title "vX.Y.Z - Title" \
  --notes "# vX.Y.Z - Title

## 🎯 Key Improvements

### Metric Name
- **Metric 1**: Before → **After** (+Change)
- **Metric 2**: Before → **After**

### 📦 New Components
- **Component 1** - Description
- **Component 2** - Description

### ✨ Improvements
- ✅ **Improvement 1** - Details
- ✅ **Improvement 2** - Details

### 🐛 Fixes
- 🔧 **Fix 1** - Details
- 🔧 **Fix 2** - Details

---

Closes PROTO-XXX" \
  --latest
```

**Example** (v0.6.4):
```bash
gh release create v0.6.4 \
  --title "v0.6.4 - Test Coverage Improvements" \
  --notes "# v0.6.4 - Test Coverage Improvements

## 🎯 Test Suite Enhancements

### Coverage Improvements
- **Overall coverage**: 39% → **42%** (+3%)
- **proto_gear.py coverage**: 52% → **61%** (+9%)
- **218 tests** passing in **4.63 seconds**

### 📦 New Test Files
- **test_capability_security.py** (19 tests)
- **test_coverage_boost.py** (22 tests)
- **test_project_detection.py** (15 tests)
- **test_setup_function.py** (16 tests)

### ✨ Quality Improvements
- ✅ **Zero memory leaks** (fixed 20+ GB RAM issue)
- ✅ **Zero hanging tests** (fixed infinite wait issue)

Closes PROTO-017" \
  --latest
```

**Verify release created**:
```bash
# View in browser
gh release view vX.Y.Z --web

# Or list releases
gh release list
```

---

## Step 9: Clean Up Main Branch

**CRITICAL**: Remove any uncommitted files before syncing branches

**Check for uncommitted changes**:
```bash
git status
```

**If you see modified or untracked files** (dogfooding files, test artifacts, etc.):

**Restore modified files**:
```bash
git restore <modified-files>
```

**Remove untracked files**:
```bash
rm -f <untracked-files>
```

**Example** (v0.6.4):
```bash
# Restore dogfooding files that were modified during testing
git restore .claude/settings.local.json AGENTS.md BRANCHING.md \
  CONTRIBUTING.md PROJECT_STATUS.md TESTING.md

# Remove generated files
rm -f ARCHITECTURE.md CODE_OF_CONDUCT.md SECURITY.md coverage_report.txt
```

**Verify clean status**:
```bash
git status
# Should show: "nothing to commit, working tree clean"
```

---

## Step 10: Sync Development Branch

**CRITICAL**: Keep development branch in sync with main after every release

**Switch to development**:
```bash
git checkout development
git pull origin development
```

**Merge main into development**:
```bash
# Fast-forward merge (if development is behind)
git merge main

# Or create merge commit
git merge main -m "chore: sync development with main (vX.Y.Z release)

Merge vX.Y.Z release changes from main:
- Summary of changes
- Key improvements
- Bug fixes

This brings development up to date with latest main branch state."
```

**Push updated development**:
```bash
git push origin development
```

**Verify sync**:
```bash
# These should show no commits (branches are in sync)
git log main..development --oneline
git log development..main --oneline
```

**Switch back to main**:
```bash
git checkout main
```

---

## Step 11: Update Documentation for Next Agent

**Document what was done** in key files:

### Option 1: Update Test Coverage Analysis (for test improvements)

**File**: `docs/dev/test-coverage-analysis.md`

Update with:
- New coverage metrics
- New test files added
- Testing approach changes
- Lessons learned

### Option 2: Update Readiness Assessment (for feature releases)

**File**: `docs/dev/readiness-assessment.md`

Update with:
- New features implemented
- Updated readiness scores
- Progress since last assessment

### Always: Commit Documentation Updates

```bash
git add docs/dev/*.md
git commit -m "docs(release): document vX.Y.Z changes

- Update coverage analysis
- Document new testing approach
- Capture lessons learned"
git push origin main
```

**Example** (v0.6.4):
```bash
git add docs/dev/test-coverage-analysis.md
git commit -m "docs(testing): document UI testing approach and coverage philosophy

- Explain why 42% is optimal coverage
- Document removal of UI testing functions
- Provide examples and recommendations"
git push origin main
```

---

## Step 12: Prepare Agent Handoff

**Create handoff summary** covering:

### Repository State
```markdown
## Current State

| Component | Status | Value |
|-----------|--------|-------|
| **Main Branch** | Clean | Commit `<hash>` |
| **Development Branch** | Synced | Commit `<hash>` |
| **Version** | Released | vX.Y.Z |
| **Tests** | Passing | XXX/XXX |
| **Coverage** | Optimal | XX% |
| **GitHub Release** | Published | ✅ |
| **Working Tree** | Clean | ✅ |
```

### What Was Accomplished
```markdown
## Completed Work

1. ✅ **Feature/Fix Implementation**
   - Description of work
   - Key changes made

2. ✅ **Testing**
   - Test results
   - Coverage improvements

3. ✅ **Release Process**
   - Version bumped
   - CHANGELOG updated
   - GitHub release created
   - Branches synced
```

### Files Changed
```markdown
## Files Modified

**Added**:
- `path/to/new/file.py` - Description

**Modified**:
- `path/to/changed/file.py` - What changed

**Removed**:
- `path/to/old/file.py` - Why removed
```

### Next Steps (if any)
```markdown
## For Next Agent

**Immediate Tasks**: None (release complete)

**Future Considerations**:
- Potential improvement 1
- Potential improvement 2

**Documentation**:
- Where to find details about this release
```

---

## Complete Release Checklist

Use this checklist for EVERY release:

### Pre-Release
- [ ] All feature work completed and tested
- [ ] All tests passing locally
- [ ] Working directory clean
- [ ] On correct branch (`main` for release work)

### Feature Branch & PR
- [ ] Created feature branch from main
- [ ] Completed work with atomic commits
- [ ] Pushed branch to remote
- [ ] Created PR with gh CLI
- [ ] PR reviewed (self-review if solo)
- [ ] PR merged and branch deleted

### Versioning
- [ ] Version bumped in `pyproject.toml`
- [ ] Version bumped in `core/proto_gear_pkg/__init__.py`
- [ ] Version bump committed and pushed

### CHANGELOG
- [ ] CHANGELOG.md updated with new version
- [ ] Release notes include: Changed, Added, Fixed, Technical
- [ ] CHANGELOG committed and pushed

### Git Tag & Release
- [ ] Git tag created with full release notes
- [ ] Tag pushed to remote
- [ ] GitHub release created with `gh release create`
- [ ] Release verified in browser

### Cleanup
- [ ] Main branch cleaned (no uncommitted files)
- [ ] Working tree verified clean
- [ ] Development branch synced with main
- [ ] Both branches pushed to remote

### Documentation
- [ ] Relevant docs updated (test-coverage-analysis.md, etc.)
- [ ] Documentation committed and pushed
- [ ] Agent handoff prepared (if needed)

### Verification
- [ ] Main and development branches in sync
- [ ] GitHub release visible
- [ ] Tests still passing
- [ ] Version correct everywhere

---

## Real-World Example: v0.6.4 Release

**Full execution** of this workflow (2025-11-14):

### Step 1-2: Feature Branch
```bash
git checkout main
git pull origin main
git checkout -b test/PROTO-017-improve-test-coverage
# ... work completed over multiple commits ...
```

### Step 3: PR Created
```bash
git push -u origin test/PROTO-017-improve-test-coverage
gh pr create --base main --title "test(coverage): improve test coverage to 42%" --body "..."
```

### Step 4: PR Merged
```bash
gh pr view --web  # Review
git checkout main
git merge test/PROTO-017-improve-test-coverage --no-ff
git push origin main
git branch -d test/PROTO-017-improve-test-coverage
git push origin --delete test/PROTO-017-improve-test-coverage
```

### Step 5: Version Bump
```bash
# Updated pyproject.toml: 0.6.3 → 0.6.4
# Updated __init__.py: 0.6.3 → 0.6.4
git add pyproject.toml core/proto_gear_pkg/__init__.py
git commit -m "chore(release): bump version to v0.6.4"
git push origin main
```

### Step 6: CHANGELOG
```bash
# Added v0.6.4 section to CHANGELOG.md
git add CHANGELOG.md
git commit -m "docs(changelog): add v0.6.4 release notes"
git push origin main
```

### Step 7: Git Tag
```bash
git tag -a v0.6.4 -m "Release v0.6.4 - Test Coverage Improvements..."
git push origin v0.6.4
```

### Step 8: GitHub Release
```bash
gh release create v0.6.4 --title "v0.6.4 - Test Coverage Improvements" --notes "..." --latest
```

### Step 9: Cleanup
```bash
git restore .claude/settings.local.json AGENTS.md BRANCHING.md \
  CONTRIBUTING.md PROJECT_STATUS.md TESTING.md
rm -f ARCHITECTURE.md CODE_OF_CONDUCT.md SECURITY.md coverage_report.txt
git status  # Verified clean
```

### Step 10: Sync Development
```bash
git checkout development
git pull origin development
git merge main
git push origin development
git checkout main
```

### Step 11: Documentation
```bash
# Updated docs/dev/test-coverage-analysis.md
git add docs/dev/test-coverage-analysis.md
git commit -m "docs(testing): document UI testing approach and coverage philosophy"
git push origin main
```

### Step 12: Handoff Prepared
**Result**: Complete handoff with repository state, accomplishments, and next steps documented

---

## Common Pitfalls and Solutions

### ❌ Committing directly to main
**Problem**: Skipping feature branch and PR workflow
**Solution**: ALWAYS use feature branches, even for small changes
**Fix**: If committed to main, reset and create proper branch

### ❌ Forgetting to bump version
**Problem**: Tag created without version updates
**Solution**: ALWAYS update both version files before tagging
**Fix**: Update versions, amend commit, force push tag

### ❌ Not using gh CLI for release
**Problem**: Manual GitHub release creation
**Solution**: ALWAYS use `gh release create` command
**Fix**: Delete manual release, recreate with gh CLI

### ❌ Not cleaning up main branch
**Problem**: Uncommitted files left in working directory
**Solution**: ALWAYS run `git status` and clean before syncing
**Fix**: Run cleanup commands before development sync

### ❌ Not syncing development branch
**Problem**: Development and main diverge
**Solution**: ALWAYS sync development after every release
**Fix**: Merge main into development immediately

### ❌ Not documenting for next agent
**Problem**: Next agent doesn't know what was done
**Solution**: ALWAYS update docs and prepare handoff
**Fix**: Add documentation in follow-up commit

---

## Workflow Variants

### Quick Patch Release (Emergency Fix)
For urgent bug fixes, streamline steps 1-4:
```bash
# Create hotfix branch
git checkout -b hotfix/vX.Y.Z-critical-fix

# Make fix, commit, push
git add .
git commit -m "fix(critical): emergency fix"
git push -u origin hotfix/vX.Y.Z-critical-fix

# Create and merge PR immediately
gh pr create --base main --title "fix: critical bug" --body "Emergency fix"
gh pr merge --merge --delete-branch
```

Then continue with steps 5-12 normally.

### Solo Developer Workflow
When you're the only contributor:
- Still create feature branches (good practice)
- Self-review PRs before merging
- Can merge without external review
- Follow all other steps exactly

---

## Tools Required

### Essential
- ✅ **git** - Version control
- ✅ **gh CLI** - GitHub operations (`winget install GitHub.cli`)
- ✅ **pytest** - Running tests
- ✅ **Python 3.8+** - Development environment

### Optional
- **flake8** - Code linting
- **mypy** - Type checking
- **black** - Code formatting

---

## Success Criteria

A release is considered complete when:

- ✅ Feature branch created, worked, and merged via PR
- ✅ Version bumped in both required files
- ✅ CHANGELOG updated with release notes
- ✅ Git tag created and pushed
- ✅ GitHub release created with gh CLI
- ✅ Main branch cleaned (working tree clean)
- ✅ Development branch synced with main
- ✅ Documentation updated
- ✅ Agent handoff prepared
- ✅ All tests passing
- ✅ No uncommitted changes
- ✅ Branches verified in sync

---

## For Next Agent

When picking up after a release:

1. **Check branch status**: `git status` on both main and development
2. **Verify last release**: `gh release list`
3. **Read CHANGELOG**: See what was just released
4. **Check documentation**: Read updated docs for context
5. **Review handoff notes**: Understand current state

---

**Workflow Version**: 2.0.0
**Last Updated**: 2025-11-14 (v0.6.4 release)
**Status**: Production-ready, battle-tested
