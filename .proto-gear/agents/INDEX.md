# Agents Index

> **Specialized agent patterns** - Agent specializations extend core agents with domain-specific expertise

## Available Agents

*No specialized agent patterns are included in this configuration.*

Specialized agents provide deep expertise in specific domains like backend development, frontend development, testing, DevOps, and security.

To add specialized agent patterns, re-run `pg init` with agent specializations enabled.

---

## What are Agent Specializations?

Agent specializations **extend** the core agents defined in AGENTS.md with:

- **Domain-specific expertise** - Deep knowledge in specialized areas
- **Specialized patterns** - Best practices for specific technologies
- **Focused workflows** - Processes tailored to the domain
- **Technology awareness** - Adapts to detected frameworks

### Core vs. Specialized Agents

**Core Agents** (in AGENTS.md):
- General-purpose collaboration patterns
- Technology-agnostic workflows
- Universal decision-making processes
- 4 core + 2 flex agent slots

**Specialized Agents** (in .proto-gear/agents/):
- Domain-specific expertise
- Technology-specific patterns
- Detailed implementation guidance
- Extends core agent capabilities

---

## Available Specializations

When enabled, Proto Gear can generate these agent specializations:

### Backend Specialist
**Extends**: Core Agent #1 (Backend/Server-side)
**Expertise**:
- REST API design and implementation
- Database schema design and queries
- Server-side business logic
- Authentication and authorization
- Data validation and transformation

**Patterns**: API design, database patterns, error handling, service layer
**Workflows**: API development, database migration

---

### Frontend Specialist
**Extends**: Core Agent #2 (Frontend/UI)
**Expertise**:
- Component architecture
- State management
- Responsive design
- User experience patterns
- Browser APIs and optimization

**Patterns**: Component design, state management, responsive design
**Workflows**: UI development, component testing

---

### Testing Specialist
**Extends**: Flex Agent slot
**Expertise**:
- Test strategy and planning
- Coverage analysis
- Test doubles (mocks, stubs, fakes)
- Performance testing
- Test automation

**Patterns**: Test strategy, coverage analysis, test doubles
**Workflows**: Test suite creation, test debugging

---

### DevOps Specialist
**Extends**: Flex Agent slot
**Expertise**:
- CI/CD pipeline design
- Containerization (Docker, Kubernetes)
- Infrastructure as Code
- Monitoring and observability
- Deployment strategies

**Patterns**: CI/CD patterns, containerization, monitoring
**Workflows**: Deployment pipeline, infrastructure setup

---

### Security Specialist
**Extends**: Flex Agent slot
**Expertise**:
- Threat modeling
- Vulnerability assessment
- Secure coding practices
- Authentication and authorization
- OWASP Top 10

**Patterns**: Threat modeling, vulnerability scanning, secure defaults
**Workflows**: Security audit, penetration testing

---

## How to Enable Agent Specializations

To add specialized agent patterns to your project:

```bash
# Re-run Proto Gear with agent specializations
pg init --with-agents

# Or specify specific agents
pg init --with-agents=backend,frontend,testing
```

This will generate:
```
.proto-gear/agents/
├── INDEX.md (this file, updated)
├── backend/
│   ├── AGENT.md
│   ├── patterns/
│   └── workflows/
├── frontend/
│   ├── AGENT.md
│   ├── patterns/
│   └── workflows/
└── testing/
    ├── AGENT.md
    ├── patterns/
    └── workflows/
```

---

## How to Use Agent Specializations

### For AI Agents

1. **Check task domain** - Is this backend, frontend, testing, etc.?
2. **Load relevant agent** - Read the AGENT.md for that specialization
3. **Apply domain expertise** - Follow patterns specific to that domain
4. **Use specialized workflows** - Execute domain-specific processes
5. **Coordinate with core agents** - Maintain collaboration patterns from AGENTS.md

### For Human Developers

Agent specializations help AI agents provide more accurate, context-aware assistance:

- **Better code quality** - Domain-specific best practices
- **Consistent patterns** - Technology-appropriate conventions
- **Faster development** - Pre-defined workflows for common tasks
- **Knowledge transfer** - Document your team's domain expertise

---

## Integration with Core Templates

### AGENTS.md
Agent specializations **extend** core agents, not replace them:
- Core agents maintain overall coordination
- Specialized agents activate for domain-specific tasks
- Both work together for comprehensive coverage

### PROJECT_STATUS.md
Specialized agents update tickets with domain-specific notes:
- Backend agents note API endpoints created
- Frontend agents note components implemented
- Testing agents note coverage improvements

### Skills and Workflows
Specialized agents use the same skills and workflows, but with domain-specific interpretation:
- Backend agent uses testing/SKILL.md for API tests
- Frontend agent uses testing/SKILL.md for component tests

---

## Adding Custom Agent Specializations

To add your own specialized agent:

1. Create directory: `agents/your-specialization/`
2. Create `AGENT.md` with YAML frontmatter:
   ```yaml
   ---
   name: "Your Agent Name"
   type: "agent"
   version: "1.0.0"
   description: "Brief description"
   tags: ["domain", "expertise"]
   category: "agent-specialization"
   relevance:
     - trigger: "keywords for this agent"
     - context: "when to activate this agent"
   extends: "AGENTS.md#core-agents"
   specialties:
     - "Area of expertise 1"
     - "Area of expertise 2"
   status: "stable"
   ---
   ```
3. Add patterns/ directory with domain-specific patterns
4. Add workflows/ directory with specialized workflows
5. Update this INDEX.md to list your new agent

---

## Directory-Level AGENTS.md Template

When creating directory-specific AGENTS.md files for sub-directories, use this template to maintain the hierarchical architecture:

```markdown
# AGENTS.md - [Directory Name] Context

> **Inheritance**: This file extends root `/AGENTS.md`
> **DO NOT** duplicate information from parent AGENTS.md files

## Local Context
**Purpose**: [What this directory contains]
**Owner**: [Which core agent owns this domain]
**Special Rules**: [Directory-specific requirements]

## Agent Instructions
### When Working Here
- [Specific instruction 1]
- [Specific instruction 2]
- [Reference parent for: general rules]

## Local Patterns
[Directory-specific patterns and conventions]

## DO NOT
- Duplicate parent documentation
- Override security/compliance rules
- Create conflicting standards
```

### Key Principles

- **DRY Documentation**: Child AGENTS.md files only contain LOCAL context and MUST NOT duplicate parent information
- **Context Inheritance**: Each directory inherits rules from parent AGENTS.md files
- **Local Overrides**: Only directory-specific instructions and patterns belong in child files
- **Consistency**: All child files follow the same template structure

---

*Proto Gear Agents Index*
