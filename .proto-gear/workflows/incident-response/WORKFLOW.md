# Incident Response Workflow

## Overview

This workflow provides a systematic approach to handling production incidents from initial detection through resolution and post-mortem. It emphasizes communication, methodical investigation, and learning from failures.

## Prerequisites

Before an incident:
- ✅ Monitoring and alerting configured
- ✅ On-call rotation established
- ✅ Communication channels identified (Slack, PagerDuty, etc.)
- ✅ Access to production logs and metrics
- ✅ Runbooks available for common scenarios

## Core Philosophy

> **Stay calm. Communicate clearly. Fix first, blame never.**

The goal is to restore service as quickly as possible while minimizing impact. Post-mortems are blameless learning opportunities.

---

## Severity Levels

| Level | Name | Description | Response Time | Examples |
|-------|------|-------------|---------------|----------|
| **P1** | Critical | Complete outage, all users affected | Immediate | Site down, data loss |
| **P2** | High | Major feature broken, many users affected | < 15 min | Payment failing, login broken |
| **P3** | Medium | Feature degraded, some users affected | < 1 hour | Slow response, partial failure |
| **P4** | Low | Minor issue, few users affected | Next business day | UI glitch, edge case bug |

---

## Workflow Steps

### Step 1: Detection & Alert

**Purpose**: Identify and acknowledge the incident

**Process**:
1. Receive alert (monitoring system, user report, or observation)
2. Acknowledge the alert to stop escalation
3. Perform initial assessment of impact
4. Determine if this is a real incident or false alarm

**Initial Assessment Questions**:
- Is the service actually affected?
- How widespread is the impact?
- When did it start?
- Are there any obvious causes (recent deploy, external service)?

**Commands**:
```bash
# Check service status
curl -I https://api.example.com/health

# Check recent deployments
git log --oneline -5 --since="2 hours ago"

# Check monitoring dashboards
# (Open Grafana, Datadog, or monitoring tool)
```

**Acknowledge Alert**:
```
ACK: Investigating [service_name] alert
- Symptom: [brief description]
- Impact: [estimated user impact]
- Started: [time]
- Investigating: [your name]
```

---

### Step 2: Triage & Severity Assessment

**Purpose**: Classify severity and determine appropriate response level

**Process**:
1. Assess user impact (how many users, which features)
2. Assess business impact (revenue, reputation, compliance)
3. Assign severity level (P1-P4)
4. Determine if incident commander needed

**Severity Decision Matrix**:

| User Impact | Business Impact | Severity |
|-------------|-----------------|----------|
| All users, core feature | Revenue loss | P1 |
| Many users, important feature | Significant | P2 |
| Some users, non-critical feature | Moderate | P3 |
| Few users, minor issue | Low | P4 |

**Update Status**:
```
TRIAGE: [service_name] incident classified as P[1-4]
- Impact: [X% of users / specific feature]
- Business impact: [revenue/reputation/compliance]
- Severity: P[N]
- IC needed: [Yes/No]
```

---

### Step 3: Assemble Response Team

**Purpose**: Get the right people involved quickly

**Process**:
1. For P1/P2: Page on-call engineers immediately
2. Identify subject matter experts for affected systems
3. Assign roles: IC (Incident Commander), Comms, Technical
4. Establish communication channel (dedicated Slack channel, war room)

**Role Assignments**:

| Role | Responsibility |
|------|----------------|
| **Incident Commander (IC)** | Coordinate response, make decisions, track timeline |
| **Technical Lead** | Direct investigation and fix efforts |
| **Communications** | Keep stakeholders informed, draft user messages |
| **Scribe** | Document timeline, actions taken, decisions |

**Commands**:
```bash
# Page on-call (PagerDuty example)
pd trigger --service production --severity P1 --message "[service] is down"

# Create incident channel (Slack example)
# /incident create [service]-outage
```

**Announcement**:
```
INCIDENT DECLARED: [Service] P[N]
- IC: [name]
- Channel: #incident-[service]-[date]
- War room: [link if video call]
- Status: Investigating
```

---

### Step 4: Initial Communication

**Purpose**: Inform stakeholders appropriately

**Process**:
1. Post incident status to internal channels
2. Draft user-facing communication (if P1/P2)
3. Set expectation for update frequency
4. Notify management/leadership (P1/P2)

**Update Frequency by Severity**:
| Severity | Internal Updates | External Updates |
|----------|-----------------|------------------|
| P1 | Every 15 min | Every 30 min |
| P2 | Every 30 min | Every 1 hour |
| P3 | Every 1 hour | As needed |
| P4 | End of day | Not needed |

**Internal Update Template**:
```
INCIDENT UPDATE [HH:MM UTC]
Status: [Investigating/Identified/Monitoring/Resolved]
Impact: [current user impact]
Action: [what we're doing now]
ETA: [if known, or "investigating"]
Next update: [time]
```

**External Status Page Update**:
```
We are currently investigating issues with [service/feature].
Some users may experience [symptom].
We are working to resolve this as quickly as possible.
Last updated: [time]
```

---

### Step 5: Investigation & Diagnosis

**Purpose**: Find the root cause

**Process**:
1. Check recent changes (deployments, config changes)
2. Analyze logs, metrics, and traces
3. Form hypotheses and test them
4. Identify root cause or contributing factors
5. Document findings

**Investigation Checklist**:
- [ ] Recent deployments in last 24h?
- [ ] Recent config changes?
- [ ] External service issues?
- [ ] Traffic patterns unusual?
- [ ] Resource exhaustion (CPU, memory, disk)?
- [ ] Database issues?
- [ ] Network problems?

**Commands**:
```bash
# Check logs (example with kubectl)
kubectl logs -l app=service-name --since=1h | grep -i error

# Check metrics
# (Open monitoring dashboard, filter to incident timeframe)

# Check recent changes
git log --oneline --since="24 hours ago"
git diff HEAD~5..HEAD

# Check external dependencies
curl -I https://external-service.com/health
```

**Document Findings**:
```
ROOT CAUSE IDENTIFIED: [brief description]
- What: [technical explanation]
- Why: [underlying cause]
- When: [when it started]
- How: [how it manifested]
- Evidence: [logs, metrics, etc.]
```

**Reference**: See skills/debugging for systematic debugging techniques

---

### Step 6: Mitigation & Stabilization

**Purpose**: Stop the bleeding - restore service quickly

**Process**:
1. Implement quick mitigation (rollback, feature flag, scale up)
2. Verify mitigation is effective
3. Monitor for stability
4. Communicate status update

**Mitigation Options** (fastest first):

| Option | Speed | When to Use |
|--------|-------|-------------|
| Feature flag disable | Seconds | Feature-specific issue |
| Rollback deployment | Minutes | Recent deploy caused it |
| Scale up resources | Minutes | Capacity issue |
| Restart services | Minutes | Memory leak, stuck state |
| DNS failover | Minutes | Regional outage |
| Hotfix deploy | 30min+ | Code fix required |

**Commands**:
```bash
# Rollback deployment (Kubernetes example)
kubectl rollout undo deployment/service-name

# Disable feature flag (LaunchDarkly example)
# (Use feature flag dashboard)

# Scale up
kubectl scale deployment/service-name --replicas=10

# Restart pods
kubectl rollout restart deployment/service-name
```

**Mitigation Update**:
```
MITIGATION APPLIED [HH:MM UTC]
Action: [what was done]
Result: [service restored / partial / no effect]
Status: [Monitoring / Further action needed]
```

---

### Step 7: Resolution & Recovery

**Purpose**: Fully resolve the issue

**Process**:
1. If mitigation was temporary, implement permanent fix
2. Verify full functionality is restored
3. Confirm no side effects from fix
4. Run validation checks
5. Update incident status to resolved

**Resolution Checklist**:
- [ ] Root cause addressed (not just symptoms)
- [ ] All affected features working
- [ ] No error spikes in logs
- [ ] Metrics returned to normal
- [ ] No customer complaints incoming
- [ ] Monitoring alerts cleared

**If Code Fix Needed**:
- Follow [Hotfix Workflow](../hotfix/WORKFLOW.md)
- Emergency PR process (expedited review)
- Deploy to production with careful monitoring

**Resolution Update**:
```
INCIDENT RESOLVED [HH:MM UTC]
Duration: [X hours Y minutes]
Root cause: [brief explanation]
Resolution: [what fixed it]
Status: Monitoring for recurrence
```

---

### Step 8: Communication & Closure

**Purpose**: Close out the incident properly

**Process**:
1. Send final resolution communication
2. Update status page (if external)
3. Thank response team
4. Schedule post-mortem meeting
5. Create follow-up tickets for any remaining work

**Internal Closure**:
```
INCIDENT CLOSED: [Service] P[N]
Duration: [X hours Y minutes]
Impact: [final impact assessment]
Root cause: [brief]
Follow-ups: [tickets created]
Post-mortem: [scheduled date/time]

Thanks to everyone who helped resolve this!
```

**External Communication** (P1/P2):
```
Resolved: [Service] issues

The issues affecting [service/feature] have been resolved.
Root cause: [customer-friendly explanation]
Impact: [what users experienced]
Duration: [start to end time]

We apologize for any inconvenience. We are conducting
a thorough review to prevent similar issues in the future.
```

**Commands**:
```bash
# Create follow-up tickets
/create-ticket "Implement circuit breaker for [service]" --type task
/create-ticket "Add monitoring for [condition]" --type task
/create-ticket "Update runbook for [scenario]" --type task
```

---

### Step 9: Post-Mortem & Learning

**Purpose**: Learn from the incident and prevent recurrence

**Process**:
1. Conduct blameless post-mortem (within 48-72 hours)
2. Document complete timeline with evidence
3. Identify root causes and contributing factors
4. Define action items with owners and due dates
5. Share learnings with broader team
6. Update runbooks and documentation

**Post-Mortem Meeting Agenda** (60-90 min):
1. Timeline review (15 min)
2. Root cause analysis (20 min)
3. What went well (10 min)
4. What could be improved (15 min)
5. Action items (20 min)

**Post-Mortem Document Template**:
```markdown
# Incident Post-Mortem: [Title]

**Date**: [Incident date]
**Duration**: [X hours Y minutes]
**Severity**: P[N]
**Author**: [Name]

## Summary
[2-3 sentence summary of what happened]

## Impact
- Users affected: [number/percentage]
- Duration: [time]
- Revenue impact: [if applicable]

## Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | Alert fired |
| HH:MM | Incident declared |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Resolved |

## Root Cause
[Detailed technical explanation]

## Contributing Factors
1. [Factor 1]
2. [Factor 2]

## What Went Well
- [Thing 1]
- [Thing 2]

## What Could Be Improved
- [Improvement 1]
- [Improvement 2]

## Action Items
| Action | Owner | Due Date | Ticket |
|--------|-------|----------|--------|
| [Action 1] | [Name] | [Date] | PROJ-XXX |
| [Action 2] | [Name] | [Date] | PROJ-XXX |

## Lessons Learned
[Key takeaways for the team]
```

**Blameless Culture**:
- Focus on systems and processes, not individuals
- "What" and "how" questions, not "who"
- Assume everyone acted with best intentions
- Goal is learning, not punishment

---

## Success Criteria

Incident is properly handled when:
- [ ] Alert acknowledged promptly
- [ ] Severity correctly assessed
- [ ] Right people involved
- [ ] Stakeholders kept informed
- [ ] Root cause identified
- [ ] Service restored
- [ ] Post-mortem conducted
- [ ] Action items created and tracked
- [ ] Runbooks updated

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Panic and chaos | Follow the process, designate IC |
| Poor communication | Regular updates, designated comms person |
| Too many cooks | Clear roles, IC makes decisions |
| Skipping post-mortem | Schedule immediately, make it mandatory |
| Blame game | Enforce blameless culture |
| No follow-up | Create tickets, assign owners, track |
| Heroics over process | Process prevents burnout and mistakes |

---

## Runbook Integration

If you have runbooks for common scenarios, check them during Step 5:

```bash
# Check runbooks directory
ls docs/runbooks/

# Common runbooks:
# - database-connection-exhausted.md
# - api-rate-limiting.md
# - memory-leak-restart.md
# - external-service-fallback.md
```

---

## Related Skills

- [Debugging](../skills/debugging/SKILL.md) - Investigation techniques

## Related Workflows

- [Hotfix](../hotfix/WORKFLOW.md) - Emergency code fix workflow
- [Bug Fix](../bug-fix/WORKFLOW.md) - Non-emergency bug fixes

## Related Commands

- `/create-ticket` - Create follow-up tickets
- `/update-status` - Track incident-related tickets

---

*Proto Gear Incident Response Workflow v1.0 - Stable*
