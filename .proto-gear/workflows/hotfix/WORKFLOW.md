# Hotfix Workflow

## Overview

Hotfix workflow is for **critical production bugs** that require immediate fixes bypassing normal development cycles. Use this ONLY for emergencies that impact production users.

## When to Use Hotfix Workflow

### ✅ Use Hotfix For:
- Production is completely down (outage)
- Data loss or corruption occurring
- Security vulnerability actively being exploited
- Critical business function broken (e.g., payments failing)
- Major performance degradation affecting all users

### ❌ Don't Use Hotfix For:
- Minor bugs that don't impact production
- Feature requests (even urgent ones)
- Bugs that can wait for normal release cycle
- Non-critical UI issues
- Performance issues affecting small subset of users

> **Rule of Thumb**: If you're unsure whether it's a hotfix, it's probably a regular bug fix.

---

## Prerequisites

Before starting hotfix:
- 🚨 Production issue is **confirmed critical**
- 🚨 Stakeholders are **notified** of issue and fix plan
- ✅ You have production access and permissions
- ✅ You can deploy to production
- ✅ Rollback plan exists

---

## Workflow Steps

### Step 1: Assess and Communicate

**Purpose**: Confirm severity and notify stakeholders

**Process**:
1. Verify production issue
2. Assess impact (users affected, business impact)
3. Determine if hotfix is warranted
4. Notify stakeholders (team lead, product owner, users if applicable)
5. Document the incident

**Severity Assessment**:
```
CRITICAL (Hotfix Required):
- Production completely down
- Data corruption ongoing
- Security breach
- Payment processing broken
- >50% of users unable to use core features

HIGH (Expedited Bug Fix):
- Important feature broken
- 10-50% of users affected
- Workaround exists
- Can wait a few hours

MEDIUM/LOW (Normal Bug Fix):
- Minor issues
- <10% of users affected
- No business impact
```

**Communication Template**:
```markdown
🚨 PRODUCTION INCIDENT - [SEVERITY]

**Issue**: [Brief description]
**Impact**: [Who is affected and how]
**Detected**: [Time]
**Status**: Hotfix in progress
**ETA**: [Expected fix time]
**Incident Lead**: [Your name]

**Updates**:
- [Time] Issue detected and confirmed
- [Time] Hotfix started
- [Time] Fix deployed (when completed)
```

**Commands**:
```bash
# Check production logs
tail -f /var/log/app/production.log

# Check error monitoring dashboard
# (Sentry, Rollbar, CloudWatch, etc.)
```

---

### Step 2: Create Hotfix Branch from Main

**Purpose**: Branch from production code (main) not development

**Process**:
1. Checkout main branch (production code)
2. Pull latest
3. Create hotfix branch with version number
4. Verify branch creation

**Branch Naming**:
```
hotfix/vX.Y.Z-<short-description>

Example: hotfix/v1.2.4-fix-payment-crash
```

**Version Number**:
- Increment patch version: v1.2.3 → v1.2.4
- Use next patch version even if not released yet

**Commands**:
```bash
# Checkout main (production code)
git checkout main

# Pull latest production code
git pull origin main

# Create hotfix branch
git checkout -b hotfix/v1.2.4-fix-payment-crash

# Verify
git branch --show-current
```

**Why Branch from Main?**
- Development branch may have untested features
- Main contains production-ready code
- Hotfix must be compatible with production

---

### Step 3: Reproduce Bug Quickly

**Purpose**: Confirm bug and understand root cause

**Process**:
1. Reproduce the issue locally (or in staging)
2. Check production logs/monitoring for clues
3. Identify root cause quickly
4. Document findings

**Fast Debugging Techniques**:

**1. Check Recent Changes**:
```bash
# What changed recently in production?
git log --oneline -10 main

# Specific file changes
git log --oneline -5 src/payments/processor.py
```

**2. Review Logs**:
```bash
# Production error logs
grep "ERROR" /var/log/app/production.log | tail -50

# Stack traces
grep -A 20 "Traceback" /var/log/app/production.log | tail -50
```

**3. Check Monitoring**:
- Error tracking dashboard (Sentry, Rollbar)
- Application monitoring (New Relic, Datadog)
- Server metrics (CPU, memory, disk)

**4. Quick Local Reproduction**:
```bash
# Use production data (sanitized) if possible
# Or create minimal reproduction case
```

**Time-Box This Step**: 15-30 minutes maximum
- If can't reproduce quickly, consider rollback
- Fix symptom if root cause unclear (document technical debt)

**Reference**: See [Debugging Skill](../skills/debugging/SKILL.md) for systematic debugging

---

### Step 4: Write Minimal Test (If Time Permits)

**Purpose**: Verify fix and prevent regression

**Process**:
1. Write minimal failing test (if time allows)
2. Test should demonstrate the bug
3. Keep it simple - this is an emergency

**Quick Test Example**:
```python
def test_payment_processing_with_null_amount():
    """Hotfix: Payment processor crashes on None amount"""
    # This should NOT crash
    result = process_payment(amount=None, card="xxxx")

    # Should return error, not crash
    assert result.success is False
    assert "amount" in result.error.lower()
```

**If No Time for Tests**:
- Fix first, test later
- Document technical debt
- Add TODO comment in code
- Create follow-up ticket

```python
# HOTFIX v1.2.4: Quick fix for production crash
# TODO: Add comprehensive tests (ticket PROJ-099)
if amount is None:
    return PaymentError("Amount is required")
```

---

### Step 5: Implement Minimal Fix

**Purpose**: Fix the bug with smallest possible change

**Process**:
1. Make minimal code change
2. Fix the symptom if root cause unclear
3. Add defensive code
4. Test manually
5. Document the fix

**Example Fix**:

**Before** (crashing code):
```python
def process_payment(amount, card):
    # Crashes if amount is None
    total = amount * 100  # Convert to cents
    charge_card(card, total)
```

**After** (hotfix):
```python
def process_payment(amount, card):
    # HOTFIX v1.2.4: Prevent crash on None amount
    # Root cause: Frontend validation bypassed in mobile app
    # TODO: Fix frontend validation (ticket PROJ-099)
    if amount is None or amount <= 0:
        logger.error(f"Invalid payment amount: {amount}")
        return PaymentError("Invalid payment amount")

    total = amount * 100  # Convert to cents
    charge_card(card, total)
```

**Hotfix Principles**:
- ✅ Minimal changes
- ✅ Fix symptom if needed (document root cause for later)
- ✅ Add defensive code (validation, null checks)
- ✅ Add logging for monitoring
- ✅ Comment clearly that this is a hotfix
- ❌ Don't refactor
- ❌ Don't add features
- ❌ Don't optimize unless necessary

**Manual Testing**:
```bash
# Test the specific broken scenario
python
>>> from payments import process_payment
>>> process_payment(None, "test-card")
PaymentError("Invalid payment amount")  # ✅ No crash

# Test normal operation still works
>>> process_payment(50.00, "test-card")
Success(charge_id="ch_123")  # ✅ Works
```

---

### Step 6: Test in Staging/Pre-Production

**Purpose**: Verify fix works before production deploy

**Process**:
1. Deploy to staging environment
2. Test the broken scenario
3. Test normal operations (smoke test)
4. Monitor for issues
5. Get approval if required

**Staging Tests**:
```bash
# Deploy to staging
./deploy-staging.sh hotfix/v1.2.4-fix-payment-crash

# Test broken scenario
curl -X POST https://staging.example.com/api/payments \
  -d '{"amount": null, "card": "tok_test"}' \
  -H "Content-Type: application/json"
# Expected: 400 error (not 500 crash)

# Test normal scenario
curl -X POST https://staging.example.com/api/payments \
  -d '{"amount": 50.00, "card": "tok_test"}' \
  -H "Content-Type: application/json"
# Expected: 200 success

# Monitor staging logs
tail -f /var/log/staging/app.log
```

**Smoke Test Checklist**:
- [ ] Broken functionality now works
- [ ] Normal functionality still works
- [ ] No new errors in logs
- [ ] Performance acceptable
- [ ] Ready for production

---

### Step 7: Deploy to Production

**Purpose**: Get fix live to users

**Process**:
1. Tag the hotfix version
2. Build production release
3. Deploy to production
4. Monitor closely
5. Verify fix worked

**Commands**:
```bash
# Tag the hotfix
git tag -a v1.2.4 -m "Hotfix: Fix payment processor crash on null amount"

# Push tag
git push origin v1.2.4

# Deploy to production (varies by setup)
./deploy-production.sh v1.2.4

# Or use CI/CD
gh workflow run deploy-production.yml --ref v1.2.4
```

**Post-Deployment Monitoring** (30-60 minutes):
```bash
# Watch production logs
tail -f /var/log/production/app.log | grep -i "payment\|error"

# Check error rates in monitoring dashboard
# - Error count should drop to zero for this issue
# - No new errors should appear
# - Response times should be normal

# Check specific metrics
# - Payment success rate
# - API error rates
# - User complaints/support tickets
```

**Rollback Plan**:
```bash
# If hotfix causes new issues, rollback immediately
./deploy-production.sh v1.2.3  # Previous version

# Or
git revert v1.2.4
./deploy-production.sh v1.2.5
```

---

### Step 8: Merge Hotfix to Main and Development

**Purpose**: Get hotfix into both main and development branches

**Process**:
1. Merge hotfix to main (production)
2. Merge hotfix to development (future releases)
3. Resolve any conflicts
4. Push both branches

**Commands**:
```bash
# Merge to main
git checkout main
git merge hotfix/v1.2.4-fix-payment-crash
git push origin main

# Merge to development
git checkout development
git merge hotfix/v1.2.4-fix-payment-crash

# If conflicts exist, resolve them
# (Development may have newer code)
git status
# Fix conflicts in editor
git add <conflicted-files>
git commit

git push origin development

# Delete hotfix branch (cleanup)
git branch -d hotfix/v1.2.4-fix-payment-crash
git push origin --delete hotfix/v1.2.4-fix-payment-crash
```

**Conflict Resolution**:
- Keep hotfix changes (they're in production)
- Merge carefully with newer development code
- Test after merging to development
- If complex, create new ticket for proper fix

---

### Step 9: Document and Follow Up

**Purpose**: Learn from incident and prevent recurrence

**Process**:
1. Update incident log
2. Create follow-up tickets
3. Document lessons learned
4. Update runbooks/documentation

**Incident Log Update**:
```markdown
## Incident: Payment Processor Crash (2025-11-08)

**Severity**: CRITICAL
**Duration**: 45 minutes (14:30-15:15 UTC)
**Impact**: All payment processing down, ~500 users affected

**Timeline**:
- 14:30 - Issue detected via monitoring alerts
- 14:35 - Incident confirmed, hotfix started
- 14:45 - Root cause identified (null amount handling)
- 14:50 - Fix implemented and tested in staging
- 15:05 - Deployed to production (v1.2.4)
- 15:15 - Verified fix working, incident resolved

**Root Cause**:
Mobile app version 2.1.0 bypassed amount validation, sending null values to API.
Backend assumed amount was always validated by frontend.

**Fix**:
Added server-side validation to reject null/invalid amounts (v1.2.4)

**Follow-Up**:
- PROJ-099: Add comprehensive payment validation tests
- PROJ-100: Fix mobile app validation (v2.1.1)
- PROJ-101: Add backend validation to all API endpoints
- PROJ-102: Update API documentation with validation rules

**Prevention**:
- Never trust client-side validation
- Add server-side validation to all inputs
- Add integration tests between mobile and backend
```

**Follow-Up Tickets**:
```markdown
### PROJ-099: Add comprehensive payment tests
**Type**: Technical Debt
**Priority**: HIGH
**Description**: Hotfix v1.2.4 was deployed without tests.
Add full test coverage for payment processing edge cases.

### PROJ-100: Fix mobile app validation
**Type**: Bug
**Priority**: HIGH
**Description**: Mobile app v2.1.0 bypasses amount validation.
Add client-side validation and update to v2.1.1.

### PROJ-101: Backend validation audit
**Type**: Technical Debt
**Priority**: MEDIUM
**Description**: Audit all API endpoints for missing server-side validation.
Never trust client input.
```

**Lessons Learned**:
- What went well: Fast detection, quick hotfix, good communication
- What could improve: Better testing, validation checklist, monitoring
- Action items: Update coding standards, add validation tests

---

## Hotfix vs Bug Fix Decision Tree

```
Is production broken RIGHT NOW?
│
├─ YES
│  │
│  ├─ Are users unable to use core features?
│  │  │
│  │  ├─ YES → Use HOTFIX workflow 🚨
│  │  └─ NO  → Use expedited BUG FIX workflow
│  │
│  └─ Is data being corrupted/lost?
│     │
│     ├─ YES → Use HOTFIX workflow 🚨
│     └─ NO  → Use BUG FIX workflow
│
└─ NO → Use normal BUG FIX workflow
```

---

## Hotfix Checklist

Before deploying hotfix:

**Investigation**:
- [ ] Production issue confirmed
- [ ] Severity justified hotfix process
- [ ] Stakeholders notified
- [ ] Root cause identified (or symptom understood)

**Development**:
- [ ] Branched from `main` (not development)
- [ ] Minimal fix implemented
- [ ] Manual testing completed
- [ ] Staging deployment successful
- [ ] Smoke tests passed

**Deployment**:
- [ ] Production deployment successful
- [ ] Monitoring shows issue resolved
- [ ] No new errors introduced
- [ ] Users/stakeholders notified of fix

**Post-Deployment**:
- [ ] Merged to main branch
- [ ] Merged to development branch
- [ ] Hotfix branch deleted
- [ ] Incident documented
- [ ] Follow-up tickets created
- [ ] Lessons learned documented

---

## Common Pitfalls

### ❌ Using Hotfix for Non-Critical Issues

**Bad**: Using hotfix for minor bugs or features

**Good**: Reserve hotfix for true production emergencies

### ❌ Branching from Development

**Bad**:
```bash
git checkout development  # Has untested features!
git checkout -b hotfix/v1.2.4-fix
```

**Good**:
```bash
git checkout main  # Production-ready code
git checkout -b hotfix/v1.2.4-fix
```

### ❌ Over-Engineering the Fix

**Bad**: Refactoring entire module during hotfix

**Good**: Minimal fix, create ticket for proper solution

### ❌ Skipping Staging

**Bad**: Deploy directly to production untested

**Good**: Always test in staging first (even if urgent)

### ❌ Not Merging Back to Development

**Bad**: Hotfix only in main, development doesn't have fix

**Good**: Merge to both main and development

---

## Success Criteria

A hotfix is complete when:

- ✅ Production issue resolved
- ✅ Users can use the system normally
- ✅ Monitoring shows no errors
- ✅ Hotfix merged to main and development
- ✅ Incident documented
- ✅ Follow-up tickets created
- ✅ Stakeholders notified

---

## Post-Incident Review

Within 24-48 hours of hotfix:

1. **Conduct Blameless Post-Mortem**
   - What happened?
   - Why did it happen?
   - How did we respond?
   - How can we prevent it?

2. **Update Documentation**
   - Runbooks
   - Incident response procedures
   - Monitoring alerts
   - Deployment checklists

3. **Schedule Follow-Up Work**
   - Proper fix (if hotfix was temporary)
   - Additional tests
   - System improvements
   - Process improvements

---

## Related Resources

- **[Bug Fix Workflow](bug-fix.template.md)** - For non-critical bugs
- **[Release Workflow](release.template.md)** - For planned releases
- **[Debugging Skill](../skills/debugging/SKILL.md)** - Debugging techniques
- **[Testing Skill](../skills/testing/SKILL.md)** - Testing strategies
- **BRANCHING.md** - Git workflow conventions

---

## Hotfix Template

Quick reference for hotfix process:

```bash
# 1. Assess (is this really a hotfix?)
# 2. Communicate
# 3. Branch from main
git checkout main
git checkout -b hotfix/v1.2.4-fix-issue

# 4. Fix minimally
# 5. Test in staging
./deploy-staging.sh hotfix/v1.2.4-fix-issue

# 6. Deploy to production
git tag -a v1.2.4 -m "Hotfix: description"
./deploy-production.sh v1.2.4

# 7. Monitor (30-60 min)
# 8. Merge back
git checkout main && git merge hotfix/v1.2.4-fix-issue
git checkout development && git merge hotfix/v1.2.4-fix-issue

# 9. Document and create follow-up tickets
```

---

*For AI Agents*: Use hotfix workflow ONLY for critical production emergencies. Branch from main (not development), make minimal fixes, test in staging, deploy quickly, monitor closely, and create follow-up tickets for proper fixes. Speed is important, but so is not making things worse.
