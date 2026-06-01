# Finalize Release Workflow

## Purpose

Complete post-release verification and setup after a version has been tagged and released to ensure the development environment is properly configured for dogfooding.

## Overview

After creating a release (via the Release Workflow), additional steps ensure:
- The package is installed locally for dogfooding
- Installation and version are verified
- Dogfooding functionality is tested
- Pending integration tasks are identified

**Trigger**: After pushing a version tag and confirming GitHub release creation

---

## Workflow Steps

### 1. Verify Release Completion

**Objective**: Confirm the release was created successfully

**Actions**:
```bash
# Check if tag exists
git tag | grep "^v$(grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/')$"

# Check if tag is on remote
git ls-remote --tags origin | grep "v$(grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/')"

# Verify GitHub release exists
# Go to: https://github.com/{{REPO_OWNER}}/{{REPO_NAME}}/releases
```

**Success Criteria**:
- ✅ Tag exists locally
- ✅ Tag pushed to remote
- ✅ GitHub release visible on releases page

---

### 2. Install Package in Editable Mode

**Objective**: Install proto-gear locally for dogfooding development

**Why Editable Mode?**
- Code changes are immediately available without reinstall
- Can test features as you develop them
- Dogfooding uses the exact code you're working on

**Actions**:
```bash
# From proto-gear root directory
cd {{PROJECT_ROOT}}

# Install in editable mode with dev dependencies
python -m pip install -e .
```

**Success Criteria**:
- ✅ Installation completes without errors
- ✅ No dependency conflicts

**Common Issues**:
- **Python not found**: Ensure Python 3.8+ is in PATH
- **Permission errors**: May need `--user` flag on some systems
- **Outdated pip**: Run `python -m pip install --upgrade pip` first

---

### 3. Verify Installation and Version

**Objective**: Confirm the package is installed with correct version

**Actions**:
```bash
# Check command is available
pg --version

# Verify version matches pyproject.toml
EXPECTED=$(grep '^version' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
INSTALLED=$(pg --version | grep -oP '\d+\.\d+\.\d+')

if [ "$EXPECTED" == "$INSTALLED" ]; then
    echo "✅ Version verified: $INSTALLED"
else
    echo "❌ Version mismatch! Expected: $EXPECTED, Got: $INSTALLED"
fi
```

**Success Criteria**:
- ✅ `pg` command is available
- ✅ Version matches pyproject.toml
- ✅ Command works from any directory

**Troubleshooting**:
- If command not found: Restart terminal or run `hash -r` (Bash) / `rehash` (Zsh)
- If wrong version: Uninstall all instances and reinstall: `pip uninstall proto-gear -y && pip install -e .`

---

### 4. Test Dogfooding Functionality

**Objective**: Verify proto-gear works on itself

**Actions**:
```bash
# Test initialization (dry run - doesn't write files)
pg init --dry-run --with-capabilities --with-branching --ticket-prefix PROTO

# Expected output: Should show template previews without errors
```

**Success Criteria**:
- ✅ Dry run completes without errors
- ✅ Templates are displayed correctly
- ✅ No import or module errors

**If Errors Occur**:
- Check for Python syntax errors in modified files
- Verify all dependencies are installed: `pip install -e .[dev]`
- Review error messages for missing modules

---

### 5. Run Verification Tests

**Objective**: Ensure all tests pass with new version

**Actions**:
```bash
# Install dev dependencies if not already installed
pip install -e .[dev]

# Run full test suite
pytest --cov=core --cov-report=term-missing

# Check current coverage
# Target: 70%+ (current baseline varies by version)
```

**Success Criteria**:
- ✅ All tests pass
- ✅ No new test failures introduced
- ✅ Coverage meets or exceeds baseline

---

### 6. Check for Pending Integration Tasks

**Objective**: Identify any post-release work that needs completion

**Actions**:
```bash
# Look for integration ticket files
ls *_INTEGRATION_TICKET.md 2>/dev/null

# Common post-release tasks to check:
# - CLI integration pending (e.g., TEMPLATES_INTEGRATION_TICKET.md)
# - Documentation updates needed
# - Example updates required
```

**If Pending Tasks Found**:
1. Review the integration ticket file
2. Assess priority and estimated time
3. Create GitHub issue if not already tracked
4. Schedule work in next sprint or milestone

**Success Criteria**:
- ✅ All pending tasks identified
- ✅ Tasks documented and prioritized
- ✅ No blocking issues for dogfooding

---

### 7. Update Dogfooding Files (Optional)

**Objective**: Regenerate project templates with latest improvements

**When to Do This**:
- ✅ If template files were modified in this release
- ✅ If PROJECT_STATUS.md format has improved
- ✅ If new capabilities were added
- ❌ Skip if templates unchanged

**Actions**:
```bash
# Backup current files
cp AGENTS.md AGENTS.md.backup
cp PROJECT_STATUS.md PROJECT_STATUS.md.backup

# Regenerate with latest templates
pg init --with-capabilities --with-branching --ticket-prefix {{TICKET_PREFIX}}

# Manually merge:
# - Restore current tickets/status from backups
# - Keep new template improvements
# - Preserve custom configurations

# Clean up
rm *.backup
```

---

### 8. Document Finalization

**Objective**: Record finalization completion

**Actions**:

Create a finalization checklist in PROJECT_STATUS.md or commit message:

```markdown
## Release v0.10.0 Finalization

**Date**: {{DATE}}
**Status**: ✅ Complete

### Verification Checks
- [x] Tag v0.10.0 exists and pushed
- [x] GitHub release created
- [x] Package installed in editable mode
- [x] Version verified: 0.10.0
- [x] Dogfooding test passed
- [x] Full test suite passed (coverage: {{COVERAGE}}%)
- [x] Pending tasks identified: {{PENDING_COUNT}}

### Post-Release Status
- Installation: ✅ Ready for dogfooding
- Tests: ✅ All passing
- Pending work: {{LIST_PENDING_TASKS}}

### Next Steps
1. Monitor GitHub issues for user feedback
2. {{PENDING_TASK_1 if exists}}
3. Plan next milestone (v{{NEXT_VERSION}})
```

---

## Success Criteria

Release is considered finalized when:

- ✅ **Installation Verified**: `pg --version` shows correct version
- ✅ **Tests Passing**: Full test suite runs without failures
- ✅ **Dogfooding Functional**: Can run `pg init --dry-run` successfully
- ✅ **Pending Tasks Documented**: All post-release work identified and tracked
- ✅ **Development Ready**: Can continue development with dogfooding setup

---

## Post-Finalization

**Immediate Actions**:
1. Monitor GitHub Issues for early feedback
2. Check GitHub Actions for any failed workflows
3. Review release notes for accuracy

**Next Sprint Planning**:
1. Address pending integration tasks
2. Incorporate user feedback
3. Update roadmap if needed
4. Plan next release milestone

---

## Anti-Patterns

❌ **Skipping Installation Verification**
- Don't assume installation worked - always verify
- Missing this can lead to discovering issues weeks later

❌ **Ignoring Test Failures**
- Never finalize if tests are failing
- Indicates release may have introduced regressions

❌ **Not Checking for Pending Tasks**
- Pending integrations can be forgotten if not documented
- Always review integration ticket files

❌ **Skipping Dogfooding Test**
- The project should work on itself - if it doesn't, users will have issues too
- This is your first line of defense for catching problems

---

## Example: v0.5.0 Finalization

**Context**: Released Universal Capabilities System with templates CLI integration pending

**Steps Taken**:
```bash
# 1. Verified release
git tag | grep v0.5.0  # ✅ exists
curl -s https://api.github.com/repos/prototowb/proto-gear/releases/tags/v0.5.0 | grep "tag_name"  # ✅ created

# 2. Installed locally
python -m pip install -e .  # ✅ successful

# 3. Verified version
pg --version  # ✅ proto-gear version 0.5.0

# 4. Tested dogfooding
pg init --dry-run --with-capabilities  # ✅ passed

# 5. Checked pending tasks
ls *_INTEGRATION_TICKET.md
# Found: TEMPLATES_INTEGRATION_TICKET.md
# Created GitHub issue: "Complete templates CLI integration"
# Scheduled for v0.6.0 milestone
```

**Outcome**:
- Finalization complete with 1 pending task (non-blocking)
- Ready for dogfooding development
- Users can manually copy templates until integration complete

---

## Related Documentation

- **Release Workflow**: Complete release process that precedes this
- **Branching Strategy**: Understanding main/development branch flow
- **Readiness Assessment**: Tracking project maturity over time

---

**Workflow Type**: Post-Release
**Frequency**: After every release tag push
**Owner**: Release Manager / Maintainers
**Estimated Time**: 15-30 minutes
