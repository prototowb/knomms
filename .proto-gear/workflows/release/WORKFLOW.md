# Release Workflow

## Overview

This workflow guides you through preparing, testing, and deploying a new software release from development to production. It covers versioning, changelog generation, testing, and deployment.

## Prerequisites

Before starting release:
- ✅ All planned features for this release are completed and merged
- ✅ All tests are passing on development branch
- ✅ PROJECT_STATUS.md shows all tickets COMPLETED
- ✅ You have deployment permissions
- ✅ Release notes are ready or can be generated

## Release Types

### Major Release (X.0.0)
- Breaking changes
- Major new features
- Architectural changes
- Example: v1.0.0 → v2.0.0

### Minor Release (x.Y.0)
- New features (backward compatible)
- Enhancements
- Deprecations
- Example: v1.2.0 → v1.3.0

### Patch Release (x.y.Z)
- Bug fixes
- Security patches
- Minor improvements
- Example: v1.2.3 → v1.2.4

---

## Workflow Steps

### Step 1: Prepare Release

**Purpose**: Plan the release and verify readiness

**Process**:
1. Review PROJECT_STATUS.md for completed tickets
2. Verify all PRs are merged to development
3. Determine version number (semver)
4. Create release ticket
5. Communicate release plan to team

**Version Number Decision**:
```
Current: v1.2.3

Breaking changes? → v2.0.0 (Major)
New features?     → v1.3.0 (Minor)
Bug fixes only?   → v1.2.4 (Patch)
```

**Release Ticket Example**:
```markdown
## 🎫 Active Tickets

| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-100 | Release v1.3.0 | release | IN_PROGRESS | release/v1.3.0 | Release Manager |
```

**Release Checklist**:
- [ ] All planned features completed
- [ ] All tests passing
- [ ] No critical bugs
- [ ] Documentation updated
- [ ] Dependencies updated
- [ ] Security scan passed

**Commands**:
```bash
# Check current version
cat package.json | grep version  # Node.js
cat pyproject.toml | grep version  # Python
git describe --tags --abbrev=0  # Git tags

# Verify development branch is clean
git checkout development
git pull origin development
git status

# Run tests
npm test  # Node.js
pytest    # Python
```

---

### Step 2: Create Release Branch

**Purpose**: Isolate release preparation from ongoing development

**Process**:
1. Checkout development branch
2. Pull latest changes
3. Create release branch
4. Verify branch creation

**Branch Naming**:
```
release/vX.Y.Z

Example: release/v1.3.0
```

**Commands**:
```bash
# Ensure on development branch
git checkout development
git pull origin development

# Create release branch
git checkout -b release/v1.3.0

# Verify
git branch --show-current

# Push release branch
git push -u origin release/v1.3.0
```

**Why Release Branch?**
- Development can continue with new features
- Release branch stabilizes for testing
- Bug fixes go to release branch
- Branch merged to both main and development when done

---

### Step 3: Update Version Numbers

**Purpose**: Increment version across all project files

**Process**:
1. Update version in package/project files
2. Update version in documentation
3. Update version in code (if applicable)
4. Commit version bump

**Files to Update** (examples):
```bash
# Node.js
package.json → "version": "1.3.0"
package-lock.json → "version": "1.3.0"

# Python
pyproject.toml → version = "1.3.0"
setup.py → version="1.3.0"
src/__version__.py → __version__ = "1.3.0"

# Documentation
README.md → Installation instructions
docs/installation.md → Version references
```

**Example Version Bump** (Python):

**Before**:
```toml
# pyproject.toml
[project]
name = "myproject"
version = "1.2.3"
```

**After**:
```toml
# pyproject.toml
[project]
name = "myproject"
version = "1.3.0"
```

**Commit Version Bump**:
```bash
# Stage version changes
git add package.json package-lock.json README.md

# Commit
git commit -m "chore(release): bump version to 1.3.0"

# Push
git push origin release/v1.3.0
```

---

### Step 4: Generate Changelog

**Purpose**: Document all changes in this release

**Process**:
1. Review commits since last release
2. Categorize changes (features, fixes, breaking changes)
3. Write user-facing changelog
4. Update CHANGELOG.md

**Get Commits Since Last Release**:
```bash
# Get all commits since last tag
git log v1.2.3..HEAD --oneline

# Get conventional commits grouped by type
git log v1.2.3..HEAD --pretty=format:"%s" | grep "^feat:" | sort
git log v1.2.3..HEAD --pretty=format:"%s" | grep "^fix:" | sort
git log v1.2.3..HEAD --pretty=format:"%s" | grep "^BREAKING:" | sort
```

**Changelog Template**:
```markdown
# Changelog

## [1.3.0] - 2025-11-08

### 🎉 New Features
- Add user authentication with JWT tokens (#42)
- Implement real-time notifications via WebSockets (#45)
- Add export to CSV functionality (#48)

### 🐛 Bug Fixes
- Fix payment processing crash with null amounts (#52)
- Resolve race condition in session management (#54)
- Fix mobile responsiveness on iPad (#56)

### 🔒 Security
- Update dependencies to patch CVE-2025-1234 (#50)
- Add rate limiting to API endpoints (#51)

### 📚 Documentation
- Add API authentication guide (#43)
- Update deployment instructions (#47)

### ⚠️ Breaking Changes
- Remove deprecated `/api/v1/users` endpoint (use `/api/v2/users`)
- Change authentication header from `X-Auth-Token` to `Authorization: Bearer`

### 🔧 Internal Changes
- Refactor payment processing module (#53)
- Improve test coverage to 85% (#55)

**Full Changelog**: https://github.com/org/repo/compare/v1.2.3...v1.3.0
```

**Update CHANGELOG.md**:
```bash
# Edit CHANGELOG.md
# Add new version section at the top

git add CHANGELOG.md
git commit -m "docs(release): add v1.3.0 changelog"
git push origin release/v1.3.0
```

---

### Step 5: Run Full Test Suite

**Purpose**: Verify all functionality works before release

**Process**:
1. Run unit tests
2. Run integration tests
3. Run end-to-end tests
4. Check code coverage
5. Run security scans
6. Fix any failing tests

**Testing Commands**:
```bash
# Unit tests
npm test                    # Node.js
pytest tests/unit/          # Python

# Integration tests
npm run test:integration    # Node.js
pytest tests/integration/   # Python

# E2E tests
npm run test:e2e           # Node.js
pytest tests/e2e/          # Python

# Coverage
npm run test:coverage      # Node.js
pytest --cov=src --cov-report=html  # Python

# Security scan
npm audit                  # Node.js
pip-audit                  # Python
bandit -r src/             # Python security
```

**Coverage Requirements**:
```
Minimum acceptable: 70%
Target: 80%+
Critical paths: 100%
```

**If Tests Fail**:
1. Fix the bugs (create bugfix branch from release)
2. Merge fixes back to release branch
3. Re-run tests
4. Don't release until all tests pass

---

### Step 6: Build and Package

**Purpose**: Create production-ready artifacts

**Process**:
1. Clean build artifacts
2. Build production assets
3. Run optimizations
4. Package for distribution

**Build Commands**:

**Node.js**:
```bash
# Clean
rm -rf dist/ build/

# Build
npm run build

# Verify build
ls -lh dist/

# Test built artifacts
npm run start:prod  # Test production build
```

**Python**:
```bash
# Clean
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Verify
ls -lh dist/
# Should see: myproject-1.3.0.tar.gz and myproject-1.3.0-py3-none-any.whl

# Test package
pip install dist/myproject-1.3.0-py3-none-any.whl
python -c "import myproject; print(myproject.__version__)"
```

**Build Artifacts Checklist**:
- [ ] All source files compiled/bundled
- [ ] Dependencies included
- [ ] Assets optimized (images, CSS, JS minified)
- [ ] Source maps generated (if applicable)
- [ ] Package metadata correct (version, author, license)

---

### Step 7: Deploy to Staging

**Purpose**: Test release in production-like environment

**Process**:
1. Deploy to staging environment
2. Run smoke tests
3. Manual QA testing
4. Performance testing
5. Get stakeholder approval

**Staging Deployment**:
```bash
# Deploy to staging
./scripts/deploy-staging.sh v1.3.0

# Or use CI/CD
gh workflow run deploy-staging.yml --ref release/v1.3.0

# Verify deployment
curl https://staging.example.com/api/health
```

**Smoke Tests**:
```bash
# Critical path testing
curl https://staging.example.com/api/auth/login \
  -d '{"username":"test","password":"test123"}'

curl https://staging.example.com/api/users/me \
  -H "Authorization: Bearer $TOKEN"

# Check new features work
curl https://staging.example.com/api/notifications/ws

# Verify bug fixes
# Test scenarios that were previously broken
```

**Manual QA Checklist**:
- [ ] User can log in
- [ ] New features work as expected
- [ ] Bug fixes confirmed
- [ ] No regressions in existing features
- [ ] Performance acceptable
- [ ] Mobile/responsive working
- [ ] Error handling appropriate

**Staging Sign-Off**:
- QA team approval
- Product owner approval
- Stakeholder review (if applicable)

---

### Step 8: Merge Release to Main

**Purpose**: Get release code into main (production) branch

**Process**:
1. Ensure release branch is finalized
2. Create PR from release to main
3. Get PR approved
4. Merge to main
5. Tag the release

**Create Release PR**:
```bash
# Via GitHub CLI
gh pr create \
  --base main \
  --head release/v1.3.0 \
  --title "Release v1.3.0" \
  --body-file release-notes.md

# Or via web interface
```

**PR Description Template**:
```markdown
## Release v1.3.0

### Summary
Minor release adding authentication, notifications, and export features.

### What's Included
- 3 new features
- 4 bug fixes
- 1 security update
- Breaking changes to API endpoints

### Testing
- ✅ All tests passing (coverage: 85%)
- ✅ Staging deployment successful
- ✅ QA sign-off received
- ✅ Performance acceptable

### Deployment Plan
1. Merge to main
2. Tag v1.3.0
3. Deploy to production
4. Monitor for 1 hour
5. Merge back to development

### Checklist
- [x] Version bumped to 1.3.0
- [x] CHANGELOG.md updated
- [x] All tests passing
- [x] Staging tested
- [x] QA approved
- [x] Documentation updated

### Breaking Changes
⚠️ Deprecated API endpoints removed (see migration guide)

**Full Changelog**: https://github.com/org/repo/blob/main/CHANGELOG.md#130
```

**Merge and Tag**:
```bash
# After PR approval, merge
git checkout main
git pull origin main
git merge release/v1.3.0

# Tag the release
git tag -a v1.3.0 -m "Release v1.3.0

New Features:
- User authentication
- Real-time notifications
- CSV export

See CHANGELOG.md for full details"

# Push main and tag
git push origin main
git push origin v1.3.0
```

---

### Step 9: Deploy to Production

**Purpose**: Release to production users

**Process**:
1. Deploy from tagged release
2. Monitor deployment
3. Run post-deployment tests
4. Verify functionality
5. Monitor errors and performance

**Production Deployment**:
```bash
# Deploy tagged release
./scripts/deploy-production.sh v1.3.0

# Or use CI/CD
gh workflow run deploy-production.yml --ref v1.3.0

# Verify deployment
curl https://api.example.com/health
```

**Post-Deployment Checklist**:
- [ ] Application starts successfully
- [ ] Database migrations completed
- [ ] Health check returns OK
- [ ] Critical paths functional
- [ ] No errors in logs
- [ ] Performance metrics normal

**Monitoring** (first 1-2 hours):
```bash
# Watch production logs
tail -f /var/log/production/app.log

# Monitor error rates
# Check: Sentry, Rollbar, CloudWatch, etc.

# Check application metrics
# - Response times
# - Error rates
# - Request rates
# - Database performance

# Monitor user feedback
# - Support tickets
# - User reports
# - Social media mentions
```

**Rollback Plan** (if issues occur):
```bash
# If critical issues found
./scripts/deploy-production.sh v1.2.3  # Previous version

# Or
gh workflow run deploy-production.yml --ref v1.2.3

# Document rollback reason
# Create hotfix ticket if needed
```

---

### Step 10: Finalize Release

**Purpose**: Complete release process and clean up

**Process**:
1. Merge release branch back to development
2. Create GitHub release with notes
3. Publish package (if applicable)
4. Announce release
5. Update PROJECT_STATUS.md
6. Delete release branch

**Merge to Development**:
```bash
# Merge release changes back to development
git checkout development
git pull origin development
git merge release/v1.3.0

# Push development
git push origin development
```

**Create GitHub Release**:
```bash
# Via GitHub CLI
gh release create v1.3.0 \
  --title "v1.3.0 - Authentication & Notifications" \
  --notes-file CHANGELOG.md \
  --latest

# Upload release artifacts (if applicable)
gh release upload v1.3.0 dist/*.tar.gz dist/*.whl
```

**Publish Package** (if applicable):

**Python (PyPI)**:
```bash
# Publish to PyPI
python -m twine upload dist/*

# Verify
pip install myproject==1.3.0
```

**Node.js (npm)**:
```bash
# Publish to npm
npm publish

# Verify
npm view myproject@1.3.0
```

**Announce Release**:
```markdown
**Template** (Slack, Email, Twitter):

🎉 Version 1.3.0 Released!

New in this release:
✨ User authentication with JWT
✨ Real-time notifications
✨ CSV export functionality

🐛 Bug fixes for payment processing and mobile responsiveness

⚠️ Breaking changes: See migration guide

📦 Install: pip install myproject==1.3.0
📖 Docs: https://docs.example.com
📋 Changelog: https://github.com/org/repo/releases/tag/v1.3.0
```

**Update PROJECT_STATUS.md**:
```markdown
| ID | Title | Type | Status | Branch | Assignee |
|----|-------|------|--------|--------|----------|
| PROJ-100 | Release v1.3.0 | release | COMPLETED | release/v1.3.0 | Release Manager |

## 📦 Recent Releases

- **v1.3.0** (2025-11-08) - Authentication & Notifications
- **v1.2.3** (2025-10-15) - Bug fixes
- **v1.2.0** (2025-09-01) - Dashboard improvements
```

**Cleanup**:
```bash
# Delete local release branch
git branch -d release/v1.3.0

# Delete remote release branch
git push origin --delete release/v1.3.0
```

---

## Release Checklist

Complete checklist for any release:

### Pre-Release
- [ ] All features completed and merged
- [ ] All tests passing
- [ ] PROJECT_STATUS.md updated
- [ ] Version number determined
- [ ] Release branch created
- [ ] Version numbers updated
- [ ] CHANGELOG.md generated

### Testing
- [ ] Unit tests passing (>80% coverage)
- [ ] Integration tests passing
- [ ] E2E tests passing
- [ ] Security scan clean
- [ ] Staging deployment successful
- [ ] QA sign-off received

### Release
- [ ] PR to main created and approved
- [ ] Merged to main
- [ ] Tagged (v1.3.0)
- [ ] Production deployment successful
- [ ] Post-deployment tests passed
- [ ] Monitoring shows no issues

### Post-Release
- [ ] Merged back to development
- [ ] GitHub release created
- [ ] Package published (if applicable)
- [ ] Release announced
- [ ] Documentation updated
- [ ] PROJECT_STATUS.md updated
- [ ] Release branch deleted

---

## Versioning Guidelines

### Semantic Versioning (SemVer)

**Format**: MAJOR.MINOR.PATCH (e.g., 1.3.0)

**MAJOR** (1.0.0 → 2.0.0):
- Breaking changes
- Remove/rename public APIs
- Change behavior of existing features
- Require users to update their code

**MINOR** (1.2.0 → 1.3.0):
- New features (backward compatible)
- Deprecate functionality (but don't remove)
- Enhancements to existing features
- Users can upgrade without code changes

**PATCH** (1.2.3 → 1.2.4):
- Bug fixes
- Security patches
- Performance improvements
- No new features or breaking changes

### Pre-Release Versions

**Alpha** (v1.3.0-alpha.1):
- Early testing
- Unstable
- Features may change

**Beta** (v1.3.0-beta.1):
- Feature complete
- Testing phase
- Minor changes possible

**Release Candidate** (v1.3.0-rc.1):
- Final testing
- No new features
- Only critical bug fixes

**Example Flow**:
```
v1.3.0-alpha.1 → v1.3.0-alpha.2 → v1.3.0-beta.1 → v1.3.0-rc.1 → v1.3.0
```

---

## Release Cadence

### Time-Based Releases
- **Weekly**: Patch releases (bug fixes)
- **Bi-weekly/Monthly**: Minor releases (features)
- **Quarterly/Annually**: Major releases (breaking changes)

### Feature-Based Releases
- Release when significant features are ready
- Minimum 1-2 weeks between releases
- Emergency hotfixes as needed

### Continuous Deployment
- Merge to main = automatic deployment
- Feature flags control visibility
- Gradual rollouts (10% → 50% → 100%)

---

## Common Pitfalls

### ❌ Skipping Staging

**Bad**: Deploy directly to production

**Good**: Always test in staging first

### ❌ Incomplete Testing

**Bad**: "Tests probably pass, let's ship"

**Good**: Run full test suite and verify results

### ❌ Poor Release Notes

**Bad**: "Bug fixes and improvements"

**Good**: Detailed changelog with links to issues

### ❌ Not Monitoring Post-Deploy

**Bad**: Deploy and walk away

**Good**: Monitor for 1-2 hours after deployment

### ❌ Forgetting to Merge Back

**Bad**: Release branch merged to main only

**Good**: Merge to both main AND development

---

## Rollback Procedure

If release has critical issues:

1. **Assess Impact**
   - How many users affected?
   - Data loss/corruption?
   - Workaround available?

2. **Decide: Hotfix or Rollback**
   - Quick fix (30 min)? → Hotfix
   - Complex issue? → Rollback

3. **Execute Rollback**
   ```bash
   ./scripts/deploy-production.sh v1.2.3  # Previous version
   ```

4. **Communicate**
   - Notify users of rollback
   - Explain issue
   - Provide timeline for fix

5. **Fix and Re-Release**
   - Create hotfix branch
   - Fix the issue
   - Test thoroughly
   - Deploy as v1.3.1

---

## Success Criteria

A release is successful when:

- ✅ Deployed to production without issues
- ✅ All features working as expected
- ✅ No increase in error rates
- ✅ Performance metrics acceptable
- ✅ User feedback positive
- ✅ Documentation updated
- ✅ Team notified

---

## Related Resources

- **[Hotfix Workflow](hotfix.template.md)** - Emergency production fixes
- **[Feature Development](feature-development.template.md)** - Building features
- **[Bug Fix Workflow](bug-fix.template.md)** - Fixing defects
- **[Testing Skill](../skills/testing/SKILL.md)** - Testing strategies
- **BRANCHING.md** - Git workflow
- **CHANGELOG.md** - Release history

---

*For AI Agents*: Release workflow requires careful attention to testing, versioning, and deployment. Always test in staging, monitor post-deployment, and maintain clear communication with stakeholders. A successful release is one that adds value without introducing regressions.
