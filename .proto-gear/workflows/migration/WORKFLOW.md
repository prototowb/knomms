# Migration Workflow

## Overview

This workflow provides a systematic approach to implementing breaking changes and data migrations. It emphasizes backwards compatibility, comprehensive rollback planning, and staged rollouts to minimize risk.

## Prerequisites

Before starting:
- ✅ Migration scope clearly defined and documented
- ✅ Impact assessment completed
- ✅ Stakeholders identified and informed
- ✅ Test/staging environment available
- ✅ Rollback is technically possible
- ✅ Sufficient time allocated (migrations shouldn't be rushed)

## Core Philosophy

> **Plan for failure. Every migration should be reversible until proven successful.**

The best migration is one where users don't notice anything changed.

---

## Migration Types

| Type | Complexity | Risk | Duration |
|------|------------|------|----------|
| **Schema Additive** | Low | Low | Hours |
| **Schema Destructive** | High | High | Days-Weeks |
| **Data Format Change** | Medium | Medium | Days |
| **API Breaking Change** | High | High | Weeks |
| **System Migration** | Very High | Very High | Weeks-Months |

---

## Workflow Steps

### Step 1: Planning & Assessment

**Purpose**: Define migration scope, strategy, and timeline

**Process**:
1. Document exactly what is changing
2. Identify all affected systems, services, and consumers
3. Estimate impact (users, data volume, downtime)
4. Choose migration strategy (big-bang vs incremental)
5. Create migration plan document
6. Get stakeholder approval

**Migration Plan Document**:
```markdown
# Migration Plan: [Title]

## Summary
[What is being migrated and why]

## Scope
- Systems affected: [list]
- Data volume: [estimate]
- Users affected: [estimate]

## Strategy
- [ ] Big-bang (all at once)
- [ ] Incremental (phased)
- [ ] Blue-green (parallel systems)
- [ ] Strangler fig (gradual replacement)

## Timeline
| Phase | Duration | Start | End |
|-------|----------|-------|-----|
| Planning | X days | | |
| Development | X days | | |
| Testing | X days | | |
| Canary | X days | | |
| Full rollout | X days | | |
| Cleanup | X days | | |

## Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | High/Med/Low | High/Med/Low | [Mitigation] |

## Success Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## Rollback Criteria
- [ ] [When to rollback]

## Approval
- [ ] Tech Lead
- [ ] Product Owner
- [ ] Stakeholders
```

**Commands**:
```bash
# Create migration tickets
/create-ticket "Migration Plan: [Title]" --type task
/create-ticket "Migration: Phase 1 - Preparation" --type task
/create-ticket "Migration: Phase 2 - Rollout" --type task
/create-ticket "Migration: Phase 3 - Cleanup" --type task
```

---

### Step 2: Design Backwards Compatibility

**Purpose**: Ensure smooth transition for all consumers

**Process**:
1. Design compatibility layer (if applicable)
2. Define deprecation timeline
3. Create migration path for API consumers
4. Document upgrade guide
5. Set up feature flags for gradual rollout

**Backwards Compatibility Patterns**:

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Versioned API** | Multiple API versions | `/v1/users`, `/v2/users` |
| **Adapter/Facade** | Transform old format to new | Middleware that converts requests |
| **Feature Flag** | Gradual rollout | Enable new format for % of users |
| **Dual Write** | Database migration | Write to both old and new tables |
| **Shadow Mode** | Validate new system | Run new system, compare results |

**Compatibility Layer Example**:
```python
# Adapter pattern for API compatibility
def get_user_v1(user_id):
    """Old API format"""
    user = get_user_internal(user_id)
    return {
        "id": user.id,
        "name": user.full_name,  # Old field name
        "email": user.email
    }

def get_user_v2(user_id):
    """New API format"""
    user = get_user_internal(user_id)
    return {
        "id": user.id,
        "firstName": user.first_name,  # New field names
        "lastName": user.last_name,
        "emailAddress": user.email
    }
```

**Deprecation Timeline**:
```
T+0:    Announce deprecation, release new version
T+30d:  Deprecation warnings in logs
T+60d:  Deprecation warnings in responses
T+90d:  Disable old version (or longer for major changes)
```

---

### Step 3: Prepare Rollback Plan

**Purpose**: Ensure safe retreat is always possible

**Process**:
1. Document rollback steps for each phase
2. Create and test rollback scripts
3. Identify point-of-no-return (if any)
4. Define rollback decision criteria
5. Practice rollback in staging

**Rollback Plan Template**:
```markdown
# Rollback Plan: [Migration Title]

## Quick Rollback (< 5 min)
For: [Minor issues, feature flag changes]
Steps:
1. Disable feature flag: `flag set migration_v2 false`
2. Verify: [check URL/metric]
3. Communicate: "Rolled back, investigating"

## Standard Rollback (< 30 min)
For: [Deployment issues, data issues]
Steps:
1. [Step 1]
2. [Step 2]
3. [Step 3]
Verification: [how to confirm rollback worked]

## Full Rollback (< 2 hours)
For: [Major issues requiring data restoration]
Steps:
1. [Step 1 - stop writes]
2. [Step 2 - restore data]
3. [Step 3 - restart services]
4. [Step 4 - verify]

## Point of No Return
After [specific milestone], rollback is not possible because:
[Reason - e.g., old data deleted, external systems updated]

## Rollback Decision Criteria
Execute rollback if:
- [ ] Error rate > X%
- [ ] Latency > Xms
- [ ] Data corruption detected
- [ ] Customer complaints > X
- [ ] Stakeholder requests
```

**Commands**:
```bash
# Test rollback in staging
./scripts/migration-rollback.sh --env staging --dry-run
./scripts/migration-rollback.sh --env staging
```

---

### Step 4: Create Migration Scripts

**Purpose**: Build reliable, tested automation

**Process**:
1. Write forward migration scripts
2. Write reverse (rollback) migration scripts
3. Add validation and verification steps
4. Test in isolated environment
5. Document usage and parameters

**Migration Script Structure**:
```bash
scripts/
├── migrate-forward.sh      # Apply migration
├── migrate-rollback.sh     # Revert migration
├── migrate-verify.sh       # Verify migration status
├── migrate-dry-run.sh      # Preview changes
└── README.md               # Documentation
```

**Script Best Practices**:
- Idempotent: Safe to run multiple times
- Verbose: Log every action
- Checkpointed: Can resume from failure
- Verified: Check success after each step
- Documented: Clear usage instructions

**Example Migration Script**:
```bash
#!/bin/bash
# migrate-forward.sh - Database schema migration

set -euo pipefail  # Exit on error

LOG_FILE="migration_$(date +%Y%m%d_%H%M%S).log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

verify_prerequisites() {
    log "Checking prerequisites..."
    # Check database connection
    # Check permissions
    # Check disk space
}

backup_data() {
    log "Creating backup..."
    pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql
}

apply_migration() {
    log "Applying migration..."
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -f migrations/001_add_column.sql
}

verify_migration() {
    log "Verifying migration..."
    # Check new column exists
    # Check data integrity
    # Check application health
}

main() {
    log "Starting migration..."
    verify_prerequisites
    backup_data
    apply_migration
    verify_migration
    log "Migration complete!"
}

main "$@"
```

**Database Migration Example** (SQL):
```sql
-- Forward migration: 001_add_user_preferences.sql
BEGIN;

-- Add new column with default
ALTER TABLE users
ADD COLUMN preferences JSONB DEFAULT '{}';

-- Backfill existing data
UPDATE users
SET preferences = json_build_object(
    'theme', 'light',
    'notifications', true
)
WHERE preferences = '{}';

-- Add index for queries
CREATE INDEX idx_users_preferences ON users USING GIN (preferences);

COMMIT;
```

```sql
-- Rollback migration: 001_add_user_preferences_rollback.sql
BEGIN;

DROP INDEX IF EXISTS idx_users_preferences;
ALTER TABLE users DROP COLUMN IF EXISTS preferences;

COMMIT;
```

---

### Step 5: Staged Rollout - Phase 1 (Canary)

**Purpose**: Test with a small subset before full rollout

**Process**:
1. Deploy to canary/shadow environment
2. Migrate small percentage (1-5%) of data/users
3. Monitor closely for issues
4. Verify correctness and performance
5. Decision: proceed, pause, or rollback

**Canary Criteria**:
- Select representative subset (not just test accounts)
- Include edge cases if known
- Monitor for at least [X hours/days]
- Compare metrics with baseline

**Monitoring Checklist**:
- [ ] Error rates within acceptable range
- [ ] Latency unchanged (or improved)
- [ ] No data integrity issues
- [ ] No customer complaints
- [ ] Resource usage acceptable

**Canary Decision Matrix**:
| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Error rate | < 0.1% | 0.1-1% | > 1% |
| Latency p99 | < baseline+10% | +10-50% | > +50% |
| Data errors | 0 | 1-5 | > 5 |

**Commands**:
```bash
# Enable for canary users
./scripts/enable-migration.sh --percentage 5

# Monitor
./scripts/check-migration-status.sh

# Check metrics
curl http://metrics/migration-dashboard
```

---

### Step 6: Staged Rollout - Phase 2 (Expansion)

**Purpose**: Gradually expand to larger audience

**Process**:
1. Increase percentage incrementally (5% → 25% → 50% → 75%)
2. Monitor at each stage
3. Address any issues before expanding
4. Verify at scale
5. Prepare for full rollout

**Expansion Schedule**:
| Day | Percentage | Duration | Checkpoint |
|-----|------------|----------|------------|
| 1 | 5% (Canary) | 24h | Green to proceed |
| 2 | 25% | 24h | Green to proceed |
| 3 | 50% | 24h | Green to proceed |
| 4 | 75% | 24h | Green to proceed |
| 5 | 100% | - | Full rollout |

**Commands**:
```bash
# Expand to 25%
./scripts/enable-migration.sh --percentage 25

# Check health
./scripts/check-migration-health.sh

# View dashboard
open http://metrics/migration-progress
```

---

### Step 7: Full Rollout & Verification

**Purpose**: Complete the migration and verify success

**Process**:
1. Enable for 100% of users/data
2. Run comprehensive verification
3. Validate data integrity
4. Performance testing at scale
5. User acceptance testing (if applicable)
6. Declare migration complete

**Verification Checklist**:
- [ ] All data migrated successfully
- [ ] No data loss or corruption
- [ ] All features working correctly
- [ ] Performance meets requirements
- [ ] No error spikes in logs
- [ ] Monitoring alerts clear
- [ ] Stakeholder sign-off

**Data Integrity Checks**:
```sql
-- Count verification
SELECT 'old_table' as source, COUNT(*) FROM old_table
UNION ALL
SELECT 'new_table' as source, COUNT(*) FROM new_table;

-- Data verification (sample)
SELECT o.id, o.value as old_value, n.value as new_value
FROM old_table o
JOIN new_table n ON o.id = n.id
WHERE o.value != n.value
LIMIT 100;

-- Checksum verification
SELECT MD5(string_agg(data::text, '')) FROM new_table;
```

**Commands**:
```bash
# Full rollout
./scripts/enable-migration.sh --percentage 100

# Comprehensive verification
./scripts/verify-migration.sh --full

# Generate report
./scripts/migration-report.sh > migration_report.md
```

---

### Step 8: Cleanup & Documentation

**Purpose**: Remove old system and document learnings

**Process**:
1. Wait for deprecation period (typically 30-90 days)
2. Remove old code, tables, and endpoints
3. Remove compatibility layers
4. Update all documentation
5. Archive migration artifacts
6. Conduct retrospective

**Cleanup Checklist**:
- [ ] Old API endpoints removed
- [ ] Old database tables dropped (after backup)
- [ ] Compatibility code removed
- [ ] Feature flags removed
- [ ] Documentation updated
- [ ] Runbooks updated
- [ ] Migration scripts archived

**Documentation Updates**:
- API documentation (remove deprecated endpoints)
- Database schema docs
- Architecture diagrams
- Runbooks and playbooks
- CHANGELOG.md

**Cleanup Script Example**:
```bash
#!/bin/bash
# cleanup-migration.sh

# Verify migration is complete
./scripts/verify-migration.sh --status || exit 1

# Backup old data one more time
pg_dump -t old_table > final_backup_old_table.sql

# Drop old resources
psql -c "DROP TABLE old_table CASCADE;"

# Remove feature flags
./scripts/remove-feature-flag.sh migration_v2

# Archive migration scripts
mkdir -p archive/migrations/$(date +%Y%m)
mv scripts/migrate-* archive/migrations/$(date +%Y%m)/

echo "Cleanup complete!"
```

**Retrospective Questions**:
1. What went well?
2. What could be improved?
3. How accurate were our estimates?
4. What would we do differently?
5. What should we document for future migrations?

---

## Success Criteria

Migration is complete when:
- [ ] Migration plan documented and approved
- [ ] Backwards compatibility maintained (during transition)
- [ ] Rollback plan tested and documented
- [ ] Migration scripts created and tested
- [ ] Staged rollout successful
- [ ] 100% of data/users migrated
- [ ] Data integrity verified
- [ ] Performance acceptable
- [ ] Old system deprecated/removed
- [ ] Documentation updated
- [ ] Retrospective conducted

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Big-bang migration without rollback | Always have rollback plan |
| Skipping backwards compatibility | Support both old and new during transition |
| No rollback testing | Test rollback in staging before production |
| Insufficient monitoring | Set up migration-specific dashboards |
| Premature cleanup | Wait full deprecation period |
| Poor communication | Notify all stakeholders at each phase |
| Rushing the migration | Migrations take time; don't compress timeline |
| No dry-run | Always test full migration in staging first |

---

## Rollback Decision Tree

```
Issue detected during migration
            │
            v
    Is service degraded?
      /           \
    YES            NO
     │              │
     v              v
  Severity?     Monitor and
   /    \        investigate
  P1    P2+         │
   │     │          v
   v     v      Self-healing?
 Immediate  Consider  /    \
 rollback   rollback YES    NO
                      │      │
                      v      v
                   Continue  Investigate
                             more
```

---

## Related Skills

- [Testing](../skills/testing/SKILL.md) - Test coverage for migrations

## Related Workflows

- [Release](../release/WORKFLOW.md) - Release process for version bumps
- [Feature Development](../feature-development/WORKFLOW.md) - For building migration tools

## Related Commands

- `/create-ticket` - Create migration phase tickets
- `/update-status` - Track migration progress

---

*Proto Gear Migration Workflow v1.0 - Stable*
