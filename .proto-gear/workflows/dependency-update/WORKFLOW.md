# Dependency Update Workflow

**Capability Type**: Workflow
**Category**: Maintenance
**Complexity**: Intermediate
**Estimated Time**: 1-3 hours (varies by update scope)

## Overview

The Dependency Update workflow provides a systematic approach to keeping project dependencies up to date while minimizing risk of breaking changes. This workflow covers checking for updates, evaluating safety, testing changes, and handling breaking updates across different technology stacks.

## When to Use This Workflow

Use this workflow when:

- **Regular Maintenance**: Weekly or monthly dependency updates
- **Security Vulnerabilities**: Critical security patches need to be applied
- **Feature Dependencies**: Need newer version for specific features
- **End of Life**: Dependency reaching end of support
- **Breaking Changes**: Major version updates required
- **Performance Improvements**: Newer versions offer significant optimizations
- **Bug Fixes**: Dependency bugs fixed in newer versions

## Prerequisites

- **Package Manager**: npm, yarn, pip, bundler, etc. installed
- **Test Suite**: Existing tests to validate changes
- **Version Control**: Clean git working directory
- **CI/CD Pipeline**: Automated testing environment
- **Backup**: Recent backup or ability to revert changes
- **Documentation**: Changelog access for dependencies

## Workflow Steps

### Phase 1: Inventory and Analysis

**Step 1.1: Check for Outdated Dependencies**

**Node.js/npm**:
```bash
# Check for outdated packages
npm outdated

# More detailed analysis
npx npm-check-updates

# Show outdated with details
npm outdated --long
```

**Node.js/yarn**:
```bash
# Check outdated packages
yarn outdated

# Interactive upgrade
yarn upgrade-interactive

# Check for latest versions
yarn upgrade-interactive --latest
```

**Python/pip**:
```bash
# Check outdated packages
pip list --outdated

# Using pip-review
pip install pip-review
pip-review

# Check specific requirements file
pip list --outdated --format=columns | grep -f requirements.txt
```

**Ruby/bundler**:
```bash
# Check outdated gems
bundle outdated

# Check with security filter
bundle outdated --only-explicit --strict

# Show parseable format
bundle outdated --parseable
```

**Step 1.2: Categorize Updates by Risk Level**

```markdown
## Dependency Update Analysis

### Critical (Security Vulnerabilities)
**Priority**: Immediate
**Risk**: Low (if patch) to High (if major version)

- [ ] `lodash`: 4.17.15 → 4.17.21 (Critical CVE-2020-8203)
- [ ] `axios`: 0.19.0 → 0.21.2 (High severity, Prototype Pollution)
- [ ] `serialize-javascript`: 3.0.0 → 6.0.0 (Critical XSS vulnerability)

**Action**: Apply immediately, test thoroughly

### High Priority (Major Version Updates)
**Priority**: Plan carefully
**Risk**: High (breaking changes expected)

- [ ] `react`: 16.14.0 → 18.2.0 (Major: Concurrent features, new hooks)
- [ ] `webpack`: 4.46.0 → 5.75.0 (Major: Module federation, breaking changes)
- [ ] `eslint`: 7.32.0 → 8.30.0 (Major: New rules, Node.js 12+ required)

**Action**: Review migration guides, allocate time for refactoring

### Medium Priority (Minor Version Updates)
**Priority**: Regular maintenance
**Risk**: Medium (new features, potential bugs)

- [ ] `express`: 4.17.1 → 4.18.2 (Minor: New features, bug fixes)
- [ ] `jest`: 27.0.6 → 27.5.1 (Minor: Improvements, bug fixes)
- [ ] `typescript`: 4.5.5 → 4.9.4 (Minor: New features, stricter checks)

**Action**: Update during regular sprint, test thoroughly

### Low Priority (Patch Updates)
**Priority**: Routine maintenance
**Risk**: Low (bug fixes only)

- [ ] `dotenv`: 10.0.0 → 10.0.1 (Patch: Bug fixes)
- [ ] `uuid`: 8.3.2 → 8.3.3 (Patch: Minor improvements)
- [ ] `moment`: 2.29.3 → 2.29.4 (Patch: Locale updates)

**Action**: Batch update, basic smoke testing
```

**Step 1.3: Check for Security Vulnerabilities**

**Node.js**:
```bash
# NPM audit
npm audit
npm audit --json > npm-audit-report.json

# Audit with fix suggestions
npm audit fix --dry-run

# Apply automatic fixes
npm audit fix

# Fix including breaking changes
npm audit fix --force

# Snyk scanning
npx snyk test
npx snyk test --severity-threshold=high
```

**Python**:
```bash
# Safety check
pip install safety
safety check
safety check --json --output safety-report.json

# Bandit for code vulnerabilities
pip install bandit
bandit -r . -f json -o bandit-report.json
```

**Ruby**:
```bash
# Bundle audit
gem install bundler-audit
bundle-audit check --update

# Bundler audit with verbose output
bundle-audit check --verbose
```

### Phase 2: Planning and Preparation

**Step 2.1: Review Changelogs and Breaking Changes**

```bash
# View changelog for specific package
npm view express@latest
npm view express versions --json

# Visit GitHub releases
open "https://github.com/expressjs/express/releases"

# Read migration guides
open "https://github.com/reactjs/react/blob/main/CHANGELOG.md"
```

**Create Update Plan**:
```markdown
## Update Plan: React 16 → 18 Migration

### Breaking Changes to Address

1. **Automatic Batching**
   - Impact: State updates now batch automatically in timeouts/promises
   - Action: Review state update patterns, may improve performance
   - Risk: Low (mostly improvements)

2. **Strict Mode Changes**
   - Impact: Components may mount/unmount twice in development
   - Action: Ensure effects handle cleanup properly
   - Risk: Medium (may expose bugs)

3. **React.render → ReactDOM.createRoot**
   - Impact: New rendering API required
   - Action: Update all render calls
   - Risk: High (breaking change, must update)

4. **Removed Features**
   - `ReactDOM.render` (deprecated, use `createRoot`)
   - IE 11 support (dropped)
   - React.Children utilities (some changes)

### Testing Strategy

- [ ] Run existing test suite on v16 (baseline)
- [ ] Update to v18 with createRoot
- [ ] Run test suite on v18
- [ ] Fix failing tests
- [ ] Manual testing of critical paths
- [ ] Performance testing

### Rollback Plan

- Git branch: `feature/react-18-upgrade`
- Can revert: `git checkout main`
- Dependencies locked: `package-lock.json` committed
- Estimated time: 2-4 hours
- Team availability: [Date/Time]
```

**Step 2.2: Create Feature Branch**

```bash
# Create dedicated update branch
git checkout -b deps/update-2024-01

# For major updates, use specific branches
git checkout -b deps/react-18-upgrade
git checkout -b deps/webpack-5-migration
```

### Phase 3: Apply Updates

**Step 3.1: Update Dependencies by Risk Category**

**Patch Updates (Low Risk)**:
```bash
# Node.js - Update all patch versions
npm update

# Or using npm-check-updates for patch only
npx npm-check-updates --target patch -u
npm install

# Python - Update patch versions
pip install --upgrade package-name==x.y.*

# Ruby - Update patch versions
bundle update --patch
```

**Minor Updates (Medium Risk)**:
```bash
# Node.js - Update to latest minor
npx npm-check-updates --target minor -u
npm install

# Update specific package to minor
npm install express@^4.18.0

# Python - Update to latest compatible
pip install --upgrade package-name

# Ruby - Update to latest minor
bundle update --minor
```

**Major Updates (High Risk)** - Do one at a time:
```bash
# Node.js - Update specific major version
npm install react@18 react-dom@18

# Check peer dependency warnings
npm install --legacy-peer-deps  # if needed

# Python - Update major version
pip install package-name==5.*
pip install package-name>=5.0.0,<6.0.0

# Ruby - Update major version
bundle update --major <gem-name>
```

**Step 3.2: Handle Peer Dependency Conflicts**

```bash
# Check for peer dependency issues
npm install

# If conflicts occur:
npm install --legacy-peer-deps  # Use older resolution

# Or force (use cautiously)
npm install --force

# Better: Update conflicting peers together
npm install react@18 react-dom@18 react-router-dom@6
```

**Step 3.3: Update Lock Files**

```bash
# Node.js - Regenerate lockfile
rm package-lock.json
npm install

# Or with yarn
rm yarn.lock
yarn install

# Python - Update frozen requirements
pip freeze > requirements.txt

# Or with pip-tools
pip-compile requirements.in

# Ruby - Update Gemfile.lock
bundle install
bundle update
```

### Phase 4: Code Refactoring for Breaking Changes

**Step 4.1: Address Breaking Changes**

**Example: React 16 → 18 Migration**:

```javascript
// Before (React 16)
import React from 'react';
import ReactDOM from 'react-dom';
import App from './App';

ReactDOM.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>,
    document.getElementById('root')
);

// After (React 18)
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);
```

**Example: Webpack 4 → 5 Migration**:

```javascript
// Before (Webpack 4)
module.exports = {
    // Node polyfills included by default
    node: {
        fs: 'empty',
        net: 'empty'
    }
};

// After (Webpack 5)
module.exports = {
    // Node polyfills must be explicit
    resolve: {
        fallback: {
            fs: false,
            net: false,
            crypto: require.resolve('crypto-browserify'),
            stream: require.resolve('stream-browserify')
        }
    }
};

// May need to install polyfills
// npm install crypto-browserify stream-browserify
```

**Step 4.2: Update Deprecated API Usage**

```bash
# Find deprecated API usage
grep -r "\.render(" src/  # React legacy render
grep -r "componentWillMount" src/  # Deprecated lifecycle
grep -r "UNSAFE_" src/  # Unsafe lifecycle methods

# Use automated migration tools
npx react-codemod update-react-imports
npx @mui/codemod v5.0.0 src/
```

**Step 4.3: Update Type Definitions (TypeScript)**

```bash
# Update @types packages
npm install -D @types/react@18 @types/react-dom@18

# Check for type errors
npx tsc --noEmit

# Fix type errors
# - Update component types
# - Fix prop types
# - Update event handler types
```

### Phase 5: Testing and Validation

**Step 5.1: Run Automated Tests**

```bash
# Run full test suite
npm test

# Run with coverage
npm test -- --coverage

# Run specific test categories
npm test -- --testPathPattern=integration
npm test -- --testPathPattern=unit

# Watch mode for fixing tests
npm test -- --watch
```

**Step 5.2: Lint and Type Check**

```bash
# Run linter
npm run lint

# Fix auto-fixable issues
npm run lint -- --fix

# Type check (TypeScript)
npx tsc --noEmit

# Check for unused dependencies
npx depcheck
```

**Step 5.3: Build and Bundle Testing**

```bash
# Clean build
rm -rf dist/ build/
npm run build

# Check build output
ls -lh dist/
du -sh dist/

# Compare bundle sizes
npx webpack-bundle-analyzer dist/stats.json

# Test production build locally
npm run serve
# or
npx serve -s build
```

**Step 5.4: Manual Testing Checklist**

```markdown
## Manual Testing Checklist

### Critical User Flows
- [ ] User registration and login
- [ ] Core feature functionality
- [ ] Data submission and validation
- [ ] File uploads
- [ ] API integrations
- [ ] Payment processing (if applicable)

### Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

### Performance Testing
- [ ] Page load times acceptable
- [ ] No new console errors or warnings
- [ ] Memory usage within normal range
- [ ] No visual regressions

### Accessibility
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility
- [ ] Color contrast maintained
- [ ] ARIA labels present

### Error Handling
- [ ] Error boundaries working
- [ ] API error handling
- [ ] Validation messages clear
- [ ] Graceful degradation
```

**Step 5.5: Performance Benchmarking**

```bash
# Lighthouse audit
npx lighthouse http://localhost:3000 --view

# Bundle size analysis
npm run build
npx bundlesize

# Load testing (if backend changes)
npx autocannon http://localhost:3000
```

### Phase 6: Deployment and Monitoring

**Step 6.1: Stage and Commit Changes**

```bash
# Check what changed
git status
git diff package.json

# Stage dependency changes
git add package.json package-lock.json

# Include any code changes
git add src/

# Commit with descriptive message
git commit -m "deps: update dependencies ({{DATE}})

- Update React 16.14.0 → 18.2.0 (major)
- Update webpack 4.46.0 → 5.75.0 (major)
- Update express 4.17.1 → 4.18.2 (minor)
- Update all patch-level dependencies
- Refactor React.render to createRoot API
- Update webpack config for v5 compatibility
- Fix TypeScript type errors

BREAKING CHANGE: React 18 requires createRoot API

Tested:
- All 247 tests passing
- Build size: 1.2MB → 1.1MB (-8%)
- Lighthouse score: 94/100

Closes {{TICKET_PREFIX}}-XXX

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

**Step 6.2: Create Pull Request**

```markdown
## Pull Request: Dependency Updates ({{DATE}})

### Summary
Monthly dependency maintenance update including React 18 and Webpack 5 major upgrades.

### Dependencies Updated

#### Major Updates (Breaking Changes)
- `react`: 16.14.0 → 18.2.0
- `react-dom`: 16.14.0 → 18.2.0
- `webpack`: 4.46.0 → 5.75.0

#### Minor Updates
- `express`: 4.17.1 → 4.18.2
- `jest`: 27.0.6 → 27.5.1
- `typescript`: 4.5.5 → 4.9.4

#### Security Patches
- `lodash`: 4.17.15 → 4.17.21 (CVE-2020-8203)
- `axios`: 0.19.0 → 0.21.2 (Prototype pollution)

### Code Changes

#### React 18 Migration
- Updated all `ReactDOM.render` calls to `createRoot`
- Added Strict Mode for better concurrent feature support
- Fixed component lifecycle issues exposed by new behavior

#### Webpack 5 Migration
- Updated webpack config for new Node.js polyfill system
- Added explicit crypto/stream browserify polyfills
- Removed deprecated configuration options

### Testing

- ✅ All 247 tests passing
- ✅ Build successful (bundle size: 1.2MB → 1.1MB, -8%)
- ✅ Lighthouse score: 94/100 (maintained)
- ✅ Manual testing completed
- ✅ No new console errors
- ✅ Cross-browser tested (Chrome, Firefox, Safari)

### Performance Impact

- **Bundle size**: Reduced by 8%
- **Load time**: No significant change
- **Runtime**: Improved with React 18 concurrent features

### Breaking Changes

**React 18**: Applications using `ReactDOM.render` must update to `createRoot`. Migration is straightforward and included in this PR.

### Deployment Notes

- No database migrations required
- No environment variable changes
- Can be deployed directly to production
- Rollback: Simply revert this commit if issues arise

### Checklist

- [x] All tests passing
- [x] Build successful
- [x] No security vulnerabilities
- [x] Documentation updated (if needed)
- [x] Changelog updated
- [x] Manual testing completed
- [x] Performance benchmarked

### Related Issues

Closes {{TICKET_PREFIX}}-XXX

---

**Review Notes**: Focus on React/Webpack migration patterns. All updates tested thoroughly.
```

**Step 6.3: Deploy to Staging**

```bash
# Deploy to staging environment
git push origin deps/update-2024-01

# Trigger staging deployment
npm run deploy:staging
# or via CI/CD

# Monitor staging environment
# Check logs, error tracking, performance metrics
```

**Step 6.4: Monitor Production Deployment**

```markdown
## Post-Deployment Monitoring Checklist

### Immediate (0-1 hour after deployment)
- [ ] Check error tracking dashboard (Sentry, Bugsnag, etc.)
- [ ] Monitor application logs for new errors
- [ ] Check API response times
- [ ] Verify key user flows working
- [ ] Monitor browser console for errors

### Short-term (1-24 hours)
- [ ] Review user feedback/support tickets
- [ ] Check performance metrics (page load, API latency)
- [ ] Monitor error rates (should be similar to pre-deployment)
- [ ] Verify analytics tracking working
- [ ] Check resource utilization (CPU, memory)

### Medium-term (1-7 days)
- [ ] Review bundle size impact in production
- [ ] Analyze user behavior changes
- [ ] Monitor crash rate (mobile apps)
- [ ] Check for new security vulnerability reports
- [ ] Gather team feedback on new versions
```

## Automation and Best Practices

### Automated Dependency Updates

**Dependabot (GitHub)**:
```yaml
# .github/dependabot.yml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
      time: "09:00"
    open-pull-requests-limit: 10
    reviewers:
      - "engineering-team"
    assignees:
      - "tech-lead"
    labels:
      - "dependencies"
      - "automated"
    commit-message:
      prefix: "deps"
      include: "scope"
    # Group patch updates
    groups:
      patch-updates:
        patterns:
          - "*"
        update-types:
          - "patch"
```

**Renovate Bot**:
```json
{
  "extends": ["config:base"],
  "schedule": ["after 9am every monday"],
  "timezone": "America/New_York",
  "labels": ["dependencies"],
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "automerge": true,
      "automergeType": "branch"
    },
    {
      "matchUpdateTypes": ["minor"],
      "groupName": "minor updates"
    },
    {
      "matchUpdateTypes": ["major"],
      "enabled": false
    }
  ]
}
```

### Dependency Update Policy

```markdown
## Dependency Update Policy

### Frequency
- **Security patches**: Immediate (within 24 hours)
- **Patch updates**: Weekly (every Monday)
- **Minor updates**: Monthly (first Monday of month)
- **Major updates**: Quarterly (planned during sprint planning)

### Approval Requirements
- **Patch updates**: Automated merge if tests pass
- **Minor updates**: Review by any team member
- **Major updates**: Review by tech lead + testing

### Testing Requirements
- **Patch**: Automated tests only
- **Minor**: Automated tests + smoke testing
- **Major**: Full test suite + manual QA + staging validation

### Exceptions
- **Critical security**: Override schedule, immediate deployment
- **Feature blockers**: Update dependency when needed for feature
- **EOL software**: Prioritize migration before end-of-life date
```

## Common Issues and Solutions

### Issue: Peer Dependency Conflicts

**Problem**: `npm install` fails with peer dependency errors

**Solution**:
```bash
# Option 1: Use legacy peer dep resolution
npm install --legacy-peer-deps

# Option 2: Update all related packages together
npm install react@18 react-dom@18 react-router-dom@6

# Option 3: Use npm 7+ automatic peer dep installation
npm install --save-peer
```

### Issue: Breaking Changes in Minor Version

**Problem**: "Minor" update breaks application

**Solution**:
```bash
# Pin to exact version in package.json
{
  "dependencies": {
    "problematic-package": "1.2.3"  // No ^ or ~
  }
}

# Report bug to package maintainer
# Consider switching to alternative package
```

### Issue: Bundle Size Increase

**Problem**: Update significantly increases bundle size

**Solution**:
```bash
# Analyze bundle
npx webpack-bundle-analyzer dist/stats.json

# Check for duplicate dependencies
npx duplicate-package-checker-webpack-plugin

# Consider alternatives
npm install smaller-alternative

# Use tree-shaking
import { specificFunction } from 'large-library'  # Good
import * as lib from 'large-library'  # Bad
```

## Integration with Other Skills

- **Testing**: Run test suite after updates
- **Security Auditing**: Check dependencies for vulnerabilities
- **Performance Optimization**: Monitor performance impact
- **Documentation**: Update docs if APIs change
- **Git Workflow**: Follow branching conventions

## Tools and Resources

### Dependency Analysis
- **npm-check-updates**: Find newer versions
- **npm outdated**: Check outdated packages
- **depcheck**: Find unused dependencies
- **bundlesize**: Track bundle size impact

### Security Scanning
- **npm audit**: Built-in security auditing
- **Snyk**: Comprehensive vulnerability scanning
- **WhiteSource**: Enterprise dependency security
- **OWASP Dependency-Check**: Multi-language scanner

### Automation
- **Dependabot**: GitHub automated updates
- **Renovate**: Advanced dependency automation
- **Greenkeeper**: Automated dependency management
- **npm-check**: Interactive update CLI

## Success Metrics

- **Update Frequency**: Dependencies updated weekly/monthly
- **Security Vulnerability Time-to-Fix**: <24 hours for critical
- **Dependency Freshness**: % of deps within 1 major version of latest
- **Update Failure Rate**: % of updates causing issues
- **Time to Update**: Average time to apply updates
- **Breaking Change Lead Time**: Time from announcement to migration

---

**Workflow Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
