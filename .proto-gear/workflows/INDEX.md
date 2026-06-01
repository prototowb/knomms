# Workflows Index

> **Multi-step processes** - Workflows orchestrate complete tasks from start to finish

<!-- proto-gear:capability-index begin -->

## Available Workflows (13)

_Auto-generated from `metadata.yaml`. Hand-edits inside this block are overwritten by `pg sync-indexes`._

### Bug Fix Workflow

- **ID**: `workflows/bug-fix`
- **File**: `bug-fix/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: maintenance
- **Description**: Systematic workflow for investigating and fixing software defects
- **Tags**: bug, fix, debugging, workflow, testing, regression
- **Triggers**: "bug", "defect", "error", "issue", "broken", "not working", "failing"
- **Contexts**: When existing functionality is broken; After bug reports; When tests are failing; During maintenance
- **Dependencies**: required: `skills/debugging`, `skills/testing`; optional: `commands/create-ticket`, `skills/code-review`; suggested: `commands/analyze-coverage`
- **Agent roles**: Bug Fix Agent, Debugging Agent, Maintenance Agent, Full-Stack Developer Agent, Backend Agent, Frontend Agent
- **Steps**: 9
- **Estimated duration**: 1-3 hours per bug

### CI/CD Setup Workflow

- **ID**: `workflows/cicd-setup`
- **File**: `cicd-setup/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: devops
- **Description**: Setting up continuous integration and deployment pipelines
- **Tags**: ci, cd, devops, automation, pipeline, continuous-integration
- **Triggers**: "ci cd", "continuous integration", "pipeline", "automation", "github actions", "jenkins"
- **Contexts**: When setting up new project; For automation needs; Before production deployment
- **Dependencies**: optional: `skills/testing`; suggested: `skills/documentation`, `workflows/monitoring-setup`
- **Agent roles**: DevOps Agent, CI/CD Specialist, Infrastructure Agent
- **Steps**: 8
- **Estimated duration**: 2-4 hours

### Code Review Process Workflow

- **ID**: `workflows/code-review-process`
- **File**: `code-review-process/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: development
- **Description**: Complete PR creation, review, approval, and merge workflow
- **Tags**: pr, pull-request, review, merge, collaboration, code-quality, github
- **Triggers**: "code review", "pull request", "PR", "merge", "review", "approve", "create pr", "open pr"
- **Contexts**: After feature implementation is complete; Before merging to main/development; When requesting feedback on code; During collaborative development
- **Dependencies**: required: `skills/code-review`; optional: `skills/testing`, `commands/update-status`; suggested: `workflows/feature-development`, `workflows/bug-fix`
- **Agent roles**: Code Review Agent, Full-Stack Developer Agent, Backend Agent, Frontend Agent, Team Lead Agent
- **Steps**: 7
- **Estimated duration**: 30 min - 4 hours (depends on review cycles)

### Complete Release Workflow

- **ID**: `workflows/complete-release`
- **File**: `complete-release/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: release
- **Description**: End-to-end release workflow combining all release phases
- **Tags**: release, complete, end-to-end, deployment, comprehensive
- **Triggers**: "complete release", "full release cycle", "end-to-end release"
- **Contexts**: For major releases; When comprehensive release needed
- **Dependencies**: optional: `workflows/release`, `workflows/finalize-release`; suggested: `commands/generate-changelog`
- **Agent roles**: Release Manager Agent, DevOps Agent, Team Lead Agent
- **Steps**: 15
- **Estimated duration**: 2-4 hours

### Dependency Update Workflow

- **ID**: `workflows/dependency-update`
- **File**: `dependency-update/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: maintenance
- **Description**: Systematic workflow for updating project dependencies safely
- **Tags**: dependencies, update, maintenance, security, packages
- **Triggers**: "update dependencies", "upgrade packages", "dependency maintenance", "security updates"
- **Contexts**: When dependencies are outdated; For security patches; Regular maintenance
- **Dependencies**: optional: `skills/testing`; suggested: `skills/security`, `commands/generate-changelog`
- **Agent roles**: Maintenance Agent, DevOps Agent, Security Agent
- **Steps**: 7
- **Estimated duration**: 1-2 hours

### Documentation Update Workflow

- **ID**: `workflows/documentation-update`
- **File**: `documentation-update/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: documentation
- **Description**: Systematic workflow for maintaining and updating project documentation
- **Tags**: documentation, update, maintenance, technical-writing
- **Triggers**: "update docs", "documentation", "improve docs", "docs maintenance"
- **Contexts**: After feature implementation; Before releases; When APIs change; For outdated documentation
- **Dependencies**: optional: `skills/documentation`; suggested: `workflows/feature-development`
- **Agent roles**: Documentation Agent, Technical Writer Agent, Full-Stack Developer Agent
- **Steps**: 6
- **Estimated duration**: 1-2 hours

### Feature Development Workflow

- **ID**: `workflows/feature-development`
- **File**: `feature-development/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: development
- **Description**: Complete workflow for developing new features from planning to deployment
- **Tags**: feature, development, workflow, planning, implementation, testing, deployment
- **Triggers**: "new feature", "implement feature", "build feature", "add functionality", "feature request"
- **Contexts**: When implementing new functionality; After feature planning; During sprint work
- **Dependencies**: required: `skills/testing`; optional: `skills/code-review`, `commands/create-ticket`; suggested: `skills/refactoring`, `commands/generate-changelog`
- **Agent roles**: Full-Stack Developer Agent, Feature Development Agent, Backend Agent, Frontend Agent, Team Lead Agent
- **Steps**: 7
- **Estimated duration**: 2-4 hours per feature

### Finalize Release Workflow

- **ID**: `workflows/finalize-release`
- **File**: `finalize-release/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: release
- **Description**: Final steps for completing and announcing a release
- **Tags**: release, finalize, announcement, documentation, post-release
- **Triggers**: "finalize release", "post-release", "announce release"
- **Contexts**: After release deployment; For release announcements
- **Dependencies**: optional: `workflows/release`, `commands/generate-changelog`; suggested: `skills/documentation`
- **Agent roles**: Release Manager Agent, Documentation Agent, Team Lead Agent
- **Steps**: 6
- **Estimated duration**: 30-60 minutes

### Hotfix Workflow

- **ID**: `workflows/hotfix`
- **File**: `hotfix/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: maintenance
- **Description**: Emergency workflow for critical production issues requiring immediate fixes
- **Tags**: hotfix, emergency, production, critical, urgent
- **Triggers**: "hotfix", "emergency", "production issue", "critical bug", "urgent fix"
- **Contexts**: When production is broken; During critical incidents; For security vulnerabilities
- **Dependencies**: required: `skills/debugging`, `skills/testing`; optional: `workflows/bug-fix`; suggested: `skills/code-review`
- **Agent roles**: Hotfix Agent, Emergency Response Agent, Production Support Agent, Senior Developer Agent
- **Steps**: 8
- **Estimated duration**: 30 minutes - 2 hours

### Incident Response Workflow

- **ID**: `workflows/incident-response`
- **File**: `incident-response/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: operations
- **Description**: Production issue handling from detection through resolution and post-mortem
- **Tags**: incident, production, emergency, monitoring, response, post-mortem, on-call, outage
- **Triggers**: "incident", "outage", "production down", "alert", "emergency", "page", "on-call", "P1", "critical"
- **Contexts**: When monitoring alerts fire; When users report production issues; During on-call rotations; After detecting service anomalies
- **Dependencies**: optional: `skills/debugging`, `workflows/hotfix`; suggested: `skills/testing`, `commands/create-ticket`
- **Agent roles**: Incident Commander Agent, DevOps Agent, On-Call Agent, Site Reliability Agent, Backend Agent
- **Steps**: 9
- **Estimated duration**: 15 min - 8 hours (depends on severity)

### Migration Workflow

- **ID**: `workflows/migration`
- **File**: `migration/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: development
- **Description**: Breaking change and data migration workflow with rollback planning
- **Tags**: migration, breaking-change, data, schema, backwards-compatibility, rollout, deprecation
- **Triggers**: "migration", "breaking change", "schema change", "data migration", "backwards compatibility", "major version", "deprecation", "database migration", "API migration"
- **Contexts**: When introducing breaking API changes; When changing database schemas; When migrating data between systems; For major version releases; When deprecating features
- **Dependencies**: optional: `skills/testing`, `commands/create-ticket`; suggested: `workflows/release`
- **Agent roles**: Migration Agent, Database Agent, DevOps Agent, Backend Agent, Team Lead Agent, Architect Agent
- **Steps**: 8
- **Estimated duration**: 1 day - 2 weeks (depends on scope)

### Monitoring Setup Workflow

- **ID**: `workflows/monitoring-setup`
- **File**: `monitoring-setup/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: devops
- **Description**: Setting up monitoring, logging, and alerting for production systems
- **Tags**: monitoring, logging, alerting, observability, devops
- **Triggers**: "monitoring", "logging", "alerting", "observability", "metrics"
- **Contexts**: Before production deployment; For system reliability; After infrastructure changes
- **Dependencies**: optional: `workflows/cicd-setup`; suggested: `skills/performance`
- **Agent roles**: DevOps Agent, Monitoring Specialist, Infrastructure Agent, SRE Agent
- **Steps**: 8
- **Estimated duration**: 3-5 hours

### Release Workflow

- **ID**: `workflows/release`
- **File**: `release/WORKFLOW.md`
- **Version**: 1.0.0
- **Status**: stable
- **Category**: release
- **Description**: Complete release process from preparation to deployment
- **Tags**: release, deployment, versioning, changelog, production
- **Triggers**: "release", "deploy", "version", "publish"
- **Contexts**: When preparing new release; After sprint completion; For version milestones
- **Dependencies**: optional: `commands/generate-changelog`, `workflows/finalize-release`; suggested: `skills/testing`, `skills/documentation`
- **Agent roles**: Release Manager Agent, DevOps Agent, Team Lead Agent
- **Steps**: 10
- **Estimated duration**: 1-2 hours

<!-- proto-gear:capability-index end -->

---

## How to Use Workflows

Workflows provide step-by-step guidance for accomplishing larger, multi-step tasks.

### For AI Agents

1. **Identify your task type** - Is it a feature, bug fix, refactoring, etc.?
2. **Find matching workflow** - Use trigger keywords to find the right workflow
3. **Check dependencies** - Ensure required skills/commands are available
4. **Follow step-by-step** - Execute each step in order
5. **Use native tools** - git, pytest, npm, etc. as described

### Workflow Structure

Each workflow contains:
- **Prerequisites** - What must be true before starting
- **Step-by-step process** - Numbered, actionable steps
- **Success criteria** - How to know you're done
- **Common pitfalls** - Mistakes to avoid
- **Related capabilities** - Links to relevant skills/commands

### Example: Using Feature Development Workflow

```
Task: Add user login feature

1. Read workflows/feature-development.md
2. Step 1: Create ticket in PROJECT_STATUS.md
3. Step 2: Create feature branch
4. Step 3: Write failing tests (RED)
5. Step 4: Implement feature (GREEN)
6. Step 5: Refactor code
7. Step 6: Commit changes
8. Step 7: Create pull request
```

---

## Workflow Decision Tree

**Choose the right workflow for your task:**

```
What are you working on?

├─ New functionality → feature-development.md
├─ Fixing a bug → bug-fix.md
├─ Critical production issue → hotfix.md
├─ Production incident/outage → incident-response/WORKFLOW.md
├─ Code review / PR → code-review-process/WORKFLOW.md
├─ Breaking change / data migration → migration/WORKFLOW.md
├─ Ready to release → release.md
├─ Just pushed a release tag → finalize-release.md
├─ Improving code structure → refactoring.md (if available)
├─ Making code faster → performance-optimization.md (if available)
└─ Other tasks → Check commands/ for single-action patterns
```

---

## Adding Custom Workflows

To add a new workflow to this project:

1. Create file: `workflows/your-workflow-name.md`
2. Add YAML frontmatter:
   ```yaml
   ---
   name: "Your Workflow Name"
   type: "workflow"
   version: "1.0.0"
   description: "Brief description"
   tags: ["keyword1", "keyword2"]
   category: "development"
   relevance:
     - trigger: "keywords that suggest this workflow"
     - context: "when to use this workflow"
   dependencies: ["skills/testing"]
   steps: 5
   estimated_duration: "1-2 hours"
   status: "stable"
   ---
   ```
3. Write numbered steps with clear instructions
4. Include prerequisites, success criteria, and common pitfalls
5. Update this INDEX.md to list your new workflow

---

*Proto Gear Workflows Index*
