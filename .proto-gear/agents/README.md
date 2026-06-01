# Example Agent Configurations

This directory contains 5 pre-configured agent examples for common development tasks.

## Available Agents

1. **testing-agent.yaml** - Test-Driven Development specialist
2. **bug-fix-agent.yaml** - Bug investigation and fixing specialist
3. **code-review-agent.yaml** - Code quality and review specialist
4. **documentation-agent.yaml** - Technical documentation specialist
5. **release-manager-agent.yaml** - Release and deployment specialist

## How to Use

### 1. Copy to Your Project

Copy any agent configuration file to your project's `.proto-gear/agents/` directory:

```bash
# From your project root
mkdir -p .proto-gear/agents
cp /path/to/proto-gear/capabilities/agents/testing-agent.yaml .proto-gear/agents/
```

Or use the `pg init` command with `--with-capabilities` flag to automatically copy all agents:

```bash
pg init --with-capabilities
```

### 2. Customize for Your Project

Edit the copied file to match your project's needs:

```bash
# Edit the agent configuration
nano .proto-gear/agents/testing-agent.yaml
```

**What to customize**:
- `capabilities`: Add or remove skills, workflows, commands
- `context_priority`: Adjust to your project structure
- `agent_instructions`: Tailor to your team's practices
- `required_files`: Update file names (e.g., TESTING.md → TEST_GUIDE.md)
- `tags`: Add project-specific tags

### 3. Validate Your Agent

Check that your agent configuration is valid:

```bash
pg agent validate testing-agent
```

This will:
- Check that all capabilities exist
- Detect circular dependencies
- Identify conflicts
- Suggest compatible capabilities

### 4. View Agent Details

See the full agent configuration:

```bash
pg agent show testing-agent
```

### 5. List All Agents

See all configured agents in your project:

```bash
pg agent list
```

## Agent Configuration Schema

For detailed schema documentation, see:
- `docs/dev/agent-configuration-schema.md` - Complete YAML schema spec
- `docs/dev/capability-metadata-schema-v2.md` - Capability system spec

## Composition Engine

These agents use the v0.8.0 Composition Engine which automatically:
- **Resolves dependencies**: Includes required capabilities transitively
- **Detects conflicts**: Warns about incompatible capability combinations
- **Provides recommendations**: Suggests compatible capabilities

## Creating Custom Agents

To create your own agent:

1. **Start with an example**: Copy the closest match to your needs
2. **Choose capabilities**: Run `pg capabilities list` to see available options
3. **Search for specific needs**: Use `pg capabilities search <keyword>`
4. **Get detailed info**: Use `pg capabilities show <name>`
5. **Validate before use**: Run `pg agent validate <name>`

## Agent vs Capabilities

| Feature | Capabilities | Agents |
|---------|-------------|--------|
| **What** | Building blocks (reusable) | Compositions (project-specific) |
| **Location** | Package | Project `.proto-gear/agents/` |
| **Customization** | Fixed | Fully customizable |
| **Dependencies** | Defined in metadata | Auto-resolved |

## Example Workflow

```bash
# 1. Initialize Proto Gear with capabilities
pg init --with-capabilities

# 2. List available capabilities
pg capabilities list

# 3. Search for specific capabilities
pg capabilities search testing

# 4. View agent configurations
pg agent list

# 5. Customize an agent
nano .proto-gear/agents/testing-agent.yaml

# 6. Validate your changes
pg agent validate testing-agent

# 7. View resolved capabilities (including dependencies)
pg agent show testing-agent
```

## Support

For questions or issues:
- GitHub Issues: https://github.com/proto-gear/proto-gear/issues
- Documentation: `docs/user/guides/`

---

*Proto Gear v0.8.0 - Composition Engine*
*Last Updated: 2025-12-09*
