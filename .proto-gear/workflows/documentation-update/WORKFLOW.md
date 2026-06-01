# Documentation Update Workflow

**Capability Type**: Workflow
**Category**: Documentation
**Complexity**: Intermediate
**Estimated Time**: 2-4 hours

## Overview

The Documentation Update workflow ensures documentation stays synchronized with code changes. This workflow helps teams maintain accurate, helpful documentation by establishing a systematic process for identifying outdated content and updating it alongside code changes.

## When to Use This Workflow

Use this workflow when:

- **After Feature Implementation**: New features need documentation
- **Code Refactoring**: API or architecture changes affect docs
- **Bug Fixes**: When fixes change behavior that's documented
- **Regular Maintenance**: Quarterly documentation reviews
- **Version Releases**: Before major/minor version releases
- **User Feedback**: When users report confusing documentation
- **Onboarding Issues**: New team members struggle with docs

## Prerequisites

- **Documentation exists**: README, API docs, or user guides
- **Documentation source**: Know where docs are stored (repo, wiki, external site)
- **Recent code changes**: Understanding of what changed
- **Write access**: Permissions to update documentation
- **Documentation tools**: Markdown editors, doc generators, etc.

## Workflow Steps

### Phase 1: Identify Documentation Needing Updates

**Step 1.1: Review Recent Code Changes**

```bash
# Get recent commits and changes
git log --oneline --since="2 weeks ago"

# See changed files
git diff main..development --name-only

# Look for significant changes
git diff main..development --stat

# Check specific areas
git log --oneline -- src/api/
git log --oneline -- src/components/
```

**Step 1.2: Create Documentation Update Checklist**

```markdown
## Documentation Update Checklist

### Code Changes Requiring Doc Updates

- [ ] **API Changes**:
  - [ ] New endpoints added: `/api/v2/users`, `/api/v2/posts`
  - [ ] Deprecated endpoints: `/api/v1/login` (use `/api/v2/auth` instead)
  - [ ] Changed parameters: `user_id` renamed to `userId`

- [ ] **Configuration Changes**:
  - [ ] New environment variables: `REDIS_URL`, `CACHE_TTL`
  - [ ] Changed default values: `MAX_UPLOAD_SIZE` now 10MB (was 5MB)
  - [ ] Removed config options: `LEGACY_AUTH_MODE`

- [ ] **Feature Changes**:
  - [ ] New features: Real-time notifications, dark mode
  - [ ] Modified behavior: Search now case-insensitive by default
  - [ ] Breaking changes: Authentication now requires JWT tokens

- [ ] **Installation/Setup Changes**:
  - [ ] New dependencies: Redis, WebSocket support
  - [ ] Changed requirements: Node.js 16+ required (was 14+)
  - [ ] New setup steps: Database migration required

- [ ] **Usage Examples**:
  - [ ] Outdated code examples in README
  - [ ] Screenshots showing old UI
  - [ ] Tutorial steps that no longer work

### Documentation Files to Update

- [ ] `README.md` - Main project documentation
- [ ] `docs/api/README.md` - API reference
- [ ] `docs/user-guide/` - User guides and tutorials
- [ ] `CONTRIBUTING.md` - Contributor guidelines
- [ ] `CHANGELOG.md` - Version history
- [ ] `docs/architecture.md` - Architecture documentation
- [ ] `package.json` - Package description
- [ ] Inline code comments - JSDoc/docstrings
```

**Step 1.3: Use Automated Detection Tools**

```bash
# Find TODO/FIXME comments in docs
grep -r "TODO\|FIXME" docs/ README.md

# Check for broken links
npx markdown-link-check README.md
npx markdown-link-check docs/**/*.md

# Find references to old version numbers
grep -r "v0\.5\." docs/ README.md

# Check for deprecated API references
grep -r "@deprecated" src/ | cut -d: -f1 | sort -u
```

### Phase 2: Update Documentation Content

**Step 2.1: Update README.md**

```markdown
# README.md Update Template

## Changes to Make:

### Update Version Badge
Before:
![Version](https://img.shields.io/badge/version-1.2.0-blue)

After:
![Version](https://img.shields.io/badge/version-1.3.0-blue)

### Update Installation Instructions
Before:
```bash
npm install my-package@1.2.0
```

After:
```bash
npm install my-package@1.3.0
# Note: Requires Node.js 16+ (changed from 14+)
```

### Add New Feature Documentation
```markdown
## New Features in v1.3.0

### Real-Time Notifications
Enable real-time notifications using WebSockets:

```javascript
import { NotificationClient } from 'my-package';

const client = new NotificationClient({
    url: process.env.WS_URL,
    auth: yourAuthToken
});

client.on('notification', (data) => {
    console.log('New notification:', data);
});
```

### Update Breaking Changes Section
```markdown
## Breaking Changes in v1.3.0

**Authentication Method Changed**:
- **Before**: API key in query string
- **After**: JWT token in Authorization header

Migration guide:
```javascript
// Old (deprecated)
fetch('https://api.example.com/users?api_key=xxx')

// New (required)
fetch('https://api.example.com/users', {
    headers: {
        'Authorization': `Bearer ${jwtToken}`
    }
})
```

**Step 2.2: Update API Documentation**

```markdown
# API Documentation Update

## New Endpoints

### POST /api/v2/auth/login
Authenticate user and receive JWT token.

**Request**:
```json
{
    "email": "user@example.com",
    "password": "securepassword"
}
```

**Response**:
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
        "id": "123",
        "email": "user@example.com",
        "name": "John Doe"
    },
    "expiresIn": 3600
}
```

## Deprecated Endpoints

### ~~POST /api/v1/login~~ (Deprecated)
**Status**: Deprecated in v1.3.0, will be removed in v2.0.0
**Migration**: Use `/api/v2/auth/login` instead

## Updated Parameters

### GET /api/v2/users/:userId
**Changed**: Parameter `user_id` renamed to `userId` for consistency

**Before**:
```
GET /api/v2/users?user_id=123
```

**After**:
```
GET /api/v2/users/123
```

**Step 2.3: Update Configuration Documentation**

```markdown
# Configuration Updates

## New Environment Variables

### REDIS_URL
**Type**: string
**Required**: Yes (as of v1.3.0)
**Default**: `redis://localhost:6379`
**Description**: Redis connection URL for caching and session storage

**Example**:
```bash
REDIS_URL=redis://username:password@redis.example.com:6379
```

### CACHE_TTL
**Type**: integer
**Required**: No
**Default**: `3600` (1 hour)
**Description**: Cache time-to-live in seconds

## Changed Configuration Options

### MAX_UPLOAD_SIZE
**Changed in**: v1.3.0
**Old Default**: `5242880` (5MB)
**New Default**: `10485760` (10MB)
**Reason**: User feedback requested larger file uploads

### Removed Configuration Options

### ~~LEGACY_AUTH_MODE~~ (Removed)
**Removed in**: v1.3.0
**Migration**: All authentication now uses JWT tokens. Remove this environment variable from your configuration.
```

**Step 2.4: Update Code Examples and Tutorials**

```markdown
# Tutorial Update: Getting Started

## Update Outdated Code Examples

### Authentication Example (Updated for v1.3.0)

**Old Example** (no longer works):
```javascript
// ❌ This is deprecated
const response = await fetch(`https://api.example.com/data?api_key=${apiKey}`);
```

**New Example** (v1.3.0+):
```javascript
// ✅ Use JWT authentication
const response = await fetch('https://api.example.com/data', {
    headers: {
        'Authorization': `Bearer ${jwtToken}`,
        'Content-Type': 'application/json'
    }
});
```

### Update Screenshots

**Action Items**:
- [ ] Replace screenshot in `docs/images/dashboard.png` (shows old UI)
- [ ] Add new screenshot for dark mode feature
- [ ] Update demo GIF showing authentication flow
- [ ] Regenerate API documentation with Swagger UI screenshot

**Tool**: Use [ScreenToGif](https://www.screentogif.com/) or [Kap](https://getkap.co/) for recording

### Update Interactive Examples

**Action Items**:
- [ ] Update CodeSandbox/CodePen examples with new API
- [ ] Test all embedded runnable examples
- [ ] Update Postman collection with new endpoints
- [ ] Refresh OpenAPI/Swagger spec
```

**Step 2.5: Update Inline Documentation**

```javascript
/**
 * Authenticate user and return JWT token
 *
 * @param {Object} credentials - User credentials
 * @param {string} credentials.email - User email address
 * @param {string} credentials.password - User password
 * @returns {Promise<AuthResponse>} Authentication response with JWT token
 * @throws {UnauthorizedError} If credentials are invalid
 *
 * @example
 * // v1.3.0+ - Use JWT authentication
 * const { token, user } = await authenticateUser({
 *     email: 'user@example.com',
 *     password: 'securepassword'
 * });
 *
 * // Store token for subsequent requests
 * localStorage.setItem('authToken', token);
 *
 * @since v1.3.0
 * @see {@link https://docs.example.com/auth|Authentication Guide}
 */
async function authenticateUser(credentials) {
    // Implementation
}

/**
 * @deprecated since v1.3.0 - Use authenticateUser() instead
 * @see {@link authenticateUser}
 */
async function loginWithApiKey(apiKey) {
    console.warn('loginWithApiKey is deprecated. Use authenticateUser() instead.');
    // Legacy implementation
}
```

### Phase 3: Review and Validate Documentation

**Step 3.1: Technical Review**

```bash
# Spell check
npx cspell "docs/**/*.md" README.md

# Markdown linting
npx markdownlint docs/ README.md

# Check for broken links
npx markdown-link-check README.md docs/**/*.md

# Validate code examples (if using doctest or similar)
npm run test:docs
```

**Step 3.2: Test Code Examples**

```bash
# Extract and run code examples from docs
# (using custom script or tool like doctest)

# Test API examples with actual requests
# Create test file: test-docs-examples.sh

#!/bin/bash
# Test documentation examples

API_BASE="http://localhost:3000/api/v2"
JWT_TOKEN="your-test-token"

echo "Testing authentication example..."
curl -X POST "$API_BASE/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test123"}' \
    | jq .

echo "Testing user fetch example..."
curl "$API_BASE/users/123" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    | jq .

# Run the test
chmod +x test-docs-examples.sh
./test-docs-examples.sh
```

**Step 3.3: User Perspective Review**

```markdown
## Documentation Review Checklist

### Clarity and Completeness
- [ ] Is the purpose of each feature clear?
- [ ] Are all required steps documented?
- [ ] Are prerequisites clearly stated?
- [ ] Are examples easy to understand and copy?
- [ ] Are error messages and troubleshooting covered?

### Accuracy
- [ ] Do all code examples work correctly?
- [ ] Are version numbers accurate?
- [ ] Are API endpoints and parameters correct?
- [ ] Are screenshots/GIFs up to date?
- [ ] Are external links still valid?

### Structure and Navigation
- [ ] Is the table of contents up to date?
- [ ] Are headings properly structured?
- [ ] Is related content cross-linked?
- [ ] Can users find information quickly?

### Consistency
- [ ] Is terminology consistent throughout?
- [ ] Are code formatting standards followed?
- [ ] Are naming conventions consistent?
- [ ] Is the tone and style consistent?
```

**Step 3.4: Peer Review**

```markdown
## Request Documentation Review

**To**: @team-members
**Subject**: Doc Review: v1.3.0 Updates

**Changes Summary**:
- Updated authentication documentation (API key → JWT)
- Added Real-time Notifications guide
- Updated configuration reference (new Redis requirement)
- Refreshed all code examples to v1.3.0

**Review Focus**:
- [ ] Are the migration instructions clear?
- [ ] Would a new user understand how to get started?
- [ ] Are there any confusing or unclear sections?
- [ ] Did I miss any important changes?

**Files Changed**:
- README.md
- docs/api/authentication.md
- docs/user-guide/getting-started.md
- docs/configuration.md

**Review By**: [Date]

**Feedback**: [Link to PR or doc]
```

### Phase 4: Publish and Announce Updates

**Step 4.1: Commit Documentation Changes**

```bash
# Stage documentation files
git add README.md docs/ CHANGELOG.md

# Commit with descriptive message
git commit -m "docs: update documentation for v1.3.0 release

- Update authentication guide (API key → JWT migration)
- Add real-time notifications documentation
- Update configuration reference with Redis requirement
- Refresh all code examples to v1.3.0 API
- Update screenshots to reflect current UI
- Fix broken links and typos

Closes {{TICKET_PREFIX}}-XXX"

# Push changes
git push origin docs/v1.3.0-updates
```

**Step 4.2: Update CHANGELOG.md**

```markdown
# CHANGELOG.md

## [1.3.0] - {{DATE}}

### Added
- **Real-time Notifications**: WebSocket-based notification system
- **Dark Mode Support**: User-configurable dark theme
- **Redis Caching**: Improved performance with Redis integration

### Changed
- **BREAKING**: Authentication now requires JWT tokens (API keys deprecated)
- **Configuration**: `MAX_UPLOAD_SIZE` default increased from 5MB to 10MB
- **API**: User parameter changed from `user_id` to `userId` for consistency

### Deprecated
- **POST /api/v1/login**: Use `/api/v2/auth/login` instead (removal in v2.0.0)
- **API Key Authentication**: Migrate to JWT tokens before v2.0.0

### Removed
- **LEGACY_AUTH_MODE** environment variable (no longer needed)

### Fixed
- Updated all documentation to reflect v1.3.0 changes
- Fixed broken links in API documentation
- Corrected code examples in Getting Started guide

### Migration Guide
See [MIGRATION.md](./MIGRATION.md) for detailed migration instructions.
```

**Step 4.3: Generate Documentation Site (if applicable)**

```bash
# For VuePress
npm run docs:build

# For Docusaurus
npm run build

# For MkDocs
mkdocs build

# For JSDoc
npm run docs:generate

# Deploy to documentation hosting
npm run docs:deploy
# or
vercel --prod
# or
netlify deploy --prod
```

**Step 4.4: Announce Documentation Updates**

```markdown
## Communication Template

### Internal Announcement (Slack/Teams)

📚 **Documentation Updated for v1.3.0**

We've updated all documentation to reflect changes in v1.3.0:

**Key Updates**:
- 🔐 New JWT authentication guide (API keys deprecated)
- ⚡ Real-time notifications tutorial added
- ⚙️ Configuration reference updated (Redis now required)
- 📝 All code examples refreshed

**Read the docs**: [Link to updated documentation]
**Migration guide**: [Link to MIGRATION.md]
**Questions?**: Ask in #engineering

---

### External Announcement (Blog/Changelog)

# Documentation Update: v1.3.0

We've comprehensively updated our documentation for the v1.3.0 release. Here's what's new:

## 🎯 What's Updated

### Authentication Guide
We've updated our authentication documentation to cover the new JWT-based auth system. The guide now includes:
- Step-by-step migration from API keys to JWT
- Code examples in JavaScript, Python, and cURL
- Troubleshooting common authentication issues

[Read the Authentication Guide →](https://docs.example.com/auth)

### Real-Time Notifications
New comprehensive guide for implementing real-time notifications:
- WebSocket connection setup
- Event handling patterns
- Error recovery and reconnection

[Read the Notifications Guide →](https://docs.example.com/notifications)

### Configuration Reference
Updated with all new environment variables and changed defaults:
- Redis configuration (new requirement)
- Updated upload size limits
- Removed deprecated options

[View Configuration Reference →](https://docs.example.com/config)

## 📚 All Examples Updated

Every code example across our documentation has been tested and updated to work with v1.3.0. Copy-paste with confidence!

## 🔄 Need Help Migrating?

Check out our [Migration Guide](https://docs.example.com/migration/v1.3.0) for step-by-step instructions on upgrading from v1.2.x.

## 💬 Feedback Welcome

Found something unclear? Let us know:
- [Open a documentation issue](https://github.com/org/repo/issues/new?label=documentation)
- [Edit on GitHub](https://github.com/org/repo/tree/main/docs)
- Ask in our [Discord community](https://discord.gg/example)

---

### GitHub Release Notes

Include documentation updates in release notes:

```markdown
## 📚 Documentation

- Comprehensive update for v1.3.0 features
- New authentication guide with JWT examples
- Added real-time notifications tutorial
- Updated configuration reference
- Refreshed all code examples
- Fixed broken links and outdated screenshots

**[View Full Documentation](https://docs.example.com)**
```

## Best Practices

1. **Update Docs with Code**: Make documentation updates part of your feature branches
2. **Version Documentation**: Tag or version docs alongside code releases
3. **Test Examples**: Always test code examples before publishing
4. **Keep History**: Document breaking changes and provide migration guides
5. **User-Focused**: Write from the user's perspective, not the implementation details
6. **Search Optimization**: Use clear headings and keywords for searchability
7. **Regular Reviews**: Schedule quarterly documentation audits
8. **Collect Feedback**: Add feedback mechanisms to documentation pages
9. **Measure Usage**: Track which docs are most/least visited
10. **Automate Checks**: Use CI to validate documentation (links, spelling, format)

## Integration with Other Skills

- **Documentation Writing**: Use for creating new documentation sections
- **Code Review**: Include documentation review in PR checklist
- **Testing**: Test documentation code examples
- **Release Management**: Update docs before each release
- **Git Workflow**: Create dedicated documentation branches

## Tools and Resources

### Documentation Generators
- **JSDoc**: JavaScript documentation generator
- **Sphinx**: Python documentation generator
- **Doxygen**: Multi-language documentation
- **TypeDoc**: TypeScript documentation

### Documentation Sites
- **VuePress**: Vue-powered static site generator
- **Docusaurus**: React-based documentation platform
- **MkDocs**: Markdown-based documentation
- **GitBook**: Modern documentation platform

### Validation Tools
- **markdown-link-check**: Validate markdown links
- **markdownlint**: Markdown style checker
- **cspell**: Spell checker for code
- **alex**: Catch insensitive writing
- **vale**: Prose linter

## Success Metrics

- **Documentation Coverage**: % of features with documentation
- **Documentation Freshness**: Time since last update
- **Broken Links**: Number of broken links (should be 0)
- **User Satisfaction**: Documentation helpfulness ratings
- **Support Ticket Reduction**: Fewer tickets due to better docs
- **Contribution Rate**: Documentation contributions from community

---

**Workflow Version**: 1.0.0
**Last Updated**: {{DATE}}
**Maintained By**: Proto Gear Community
