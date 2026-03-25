# GenAI Observability CLI

Command-line interface for managing the GenAI Observability Platform.

## Installation

```bash
# From PyPI
pip install genai-obs-cli

# From source
cd cli
pip install -e .
```

## Configuration

### Interactive Configuration

```bash
genai-obs configure
```

This will prompt for:
- API endpoint URL
- API key
- Default output format

### Environment Variables

```bash
export GENAI_OBS_ENDPOINT=https://api.observability.example.com
export GENAI_OBS_API_KEY=your-api-key-here
```

### Configuration File

Configuration is stored in `~/.genai-observability/config.json`:

```json
{
  "profiles": {
    "default": {
      "endpoint": "https://api.observability.example.com",
      "api_key": "your-api-key",
      "default_output": "table",
      "timeout": 30
    },
    "staging": {
      "endpoint": "https://api.staging.observability.example.com",
      "api_key": "staging-api-key"
    }
  }
}
```

Use profiles with `-p`:
```bash
genai-obs -p staging agents list
```

## Commands

### Global Options

```
--profile, -p    Configuration profile to use (default: default)
--endpoint, -e   API endpoint URL (overrides config)
--output, -o     Output format: json, table, text (default: table)
--verbose, -v    Enable verbose output
```

### Status & Health

```bash
# Check API connection
genai-obs status

# Show CLI version
genai-obs version
```

---

## Agents

Manage agent registrations.

### List Agents

```bash
genai-obs agents list [OPTIONS]

Options:
  --team TEXT       Filter by team ID
  --status TEXT     Filter by status (active, inactive, all)
  --limit INTEGER   Maximum results (default: 50)
```

**Examples:**
```bash
# List all active agents
genai-obs agents list

# List agents for a team
genai-obs agents list --team team-123

# JSON output
genai-obs agents list -o json
```

### Get Agent Details

```bash
genai-obs agents get AGENT_ID
```

**Example:**
```bash
genai-obs agents get my-agent-001
```

### Register Agent

```bash
genai-obs agents register [OPTIONS]

Options:
  --id TEXT           Unique agent ID (required)
  --name TEXT         Display name (required)
  --description TEXT  Agent description
  --team TEXT         Team ID
  --project TEXT      Project ID
  --framework TEXT    Framework (langchain, crewai, custom)
  --environment TEXT  Environment (default: dev)
```

**Example:**
```bash
genai-obs agents register \
    --id my-new-agent \
    --name "My New Agent" \
    --framework langchain \
    --team team-123 \
    --environment prod
```

### Update Agent

```bash
genai-obs agents update AGENT_ID [OPTIONS]

Options:
  --name TEXT        New display name
  --description TEXT New description
  --framework TEXT   New framework
  --active/--inactive Set active status
```

**Example:**
```bash
genai-obs agents update my-agent --name "Updated Name" --inactive
```

### Delete Agent

```bash
genai-obs agents delete AGENT_ID [OPTIONS]

Options:
  --force  Skip confirmation
```

### Agent Metrics

```bash
genai-obs agents metrics AGENT_ID [OPTIONS]

Options:
  --period TEXT  Time period: 1h, 24h, 7d, 30d (default: 24h)
```

---

## Traces

View and search execution traces.

### List Traces

```bash
genai-obs traces list [OPTIONS]

Options:
  --agent TEXT   Filter by agent ID
  --status TEXT  Filter by status (success, error, all)
  --since TEXT   Start time (ISO or relative: 1h, 24h, 7d)
  --until TEXT   End time (ISO format)
  --limit INT    Maximum results (default: 20)
```

**Examples:**
```bash
# Recent traces
genai-obs traces list

# Traces with errors in last hour
genai-obs traces list --status error --since 1h

# Traces for specific agent
genai-obs traces list --agent my-agent --limit 50
```

### Get Trace Details

```bash
genai-obs traces get TRACE_ID [OPTIONS]

Options:
  --spans/--no-spans  Include span details (default: yes)
```

**Example:**
```bash
genai-obs traces get abc123-def456-ghi789
```

### Search Traces

```bash
genai-obs traces search QUERY [OPTIONS]

Options:
  --agent TEXT  Filter by agent ID
  --since TEXT  Search window (default: 24h)
  --limit INT   Maximum results (default: 20)
```

**Example:**
```bash
genai-obs traces search "timeout error" --agent my-agent --since 7d
```

### Trace Timeline

```bash
genai-obs traces timeline TRACE_ID
```

Displays a visual timeline of the trace execution:

```
Trace: abc123-def456-ghi789
Status: success
Duration: 2.5s

Timeline:

✓ process_request (trace)
  +0ms | 2.5s
  ✓ call_claude (llm)
    +50ms | 1.2s
  ✓ search_database (tool)
    +1300ms | 800ms
  ✓ format_response (span)
    +2200ms | 300ms
```

### List Error Traces

```bash
genai-obs traces errors [OPTIONS]

Options:
  --agent TEXT  Filter by agent ID
  --since TEXT  Time window (default: 24h)
  --limit INT   Maximum results (default: 20)
```

---

## Alerts

Manage alerts and alert rules.

### List Alerts

```bash
genai-obs alerts list [OPTIONS]

Options:
  --status TEXT    Filter: open, acknowledged, resolved, all
  --severity TEXT  Filter: critical, high, medium, low, all
  --agent TEXT     Filter by agent ID
  --limit INT      Maximum results (default: 20)
```

**Examples:**
```bash
# Open alerts
genai-obs alerts list

# Critical alerts
genai-obs alerts list --severity critical

# All alerts for an agent
genai-obs alerts list --agent my-agent --status all
```

### Get Alert Details

```bash
genai-obs alerts get ALERT_ID
```

### Acknowledge Alert

```bash
genai-obs alerts ack ALERT_ID [OPTIONS]

Options:
  --note TEXT  Acknowledgment note
```

**Example:**
```bash
genai-obs alerts ack abc123 --note "Investigating root cause"
```

### Resolve Alert

```bash
genai-obs alerts resolve ALERT_ID [OPTIONS]

Options:
  --note TEXT  Resolution note
```

**Example:**
```bash
genai-obs alerts resolve abc123 --note "Fixed by increasing timeout"
```

### Alert Rules

#### List Rules

```bash
genai-obs alerts rules list [OPTIONS]

Options:
  --agent TEXT        Filter by agent ID
  --enabled/--disabled Filter by status
```

#### Create Rule

```bash
genai-obs alerts rules create [OPTIONS]

Options:
  --name TEXT       Rule name (required)
  --type TEXT       Rule type: error_rate, latency, token_usage, anomaly
  --agent TEXT      Target agent ID
  --severity TEXT   Alert severity (default: medium)
  --threshold FLOAT Threshold value
  --window INT      Evaluation window in seconds (default: 300)
```

**Examples:**
```bash
# Error rate alert
genai-obs alerts rules create \
    --name "High Error Rate" \
    --type error_rate \
    --threshold 0.05 \
    --severity high

# Latency alert
genai-obs alerts rules create \
    --name "Slow Responses" \
    --type latency \
    --agent my-agent \
    --threshold 5000 \
    --severity medium
```

#### Enable/Disable Rule

```bash
genai-obs alerts rules enable RULE_ID
genai-obs alerts rules disable RULE_ID
```

#### Delete Rule

```bash
genai-obs alerts rules delete RULE_ID [OPTIONS]

Options:
  --force  Skip confirmation
```

---

## API Keys

Manage API keys for agent authentication.

### List Keys

```bash
genai-obs api-keys list [OPTIONS]

Options:
  --agent TEXT    Filter by agent ID
  --active/--all  Show only active keys (default: active)
```

### Create Key

```bash
genai-obs api-keys create [OPTIONS]

Options:
  --name TEXT    Key name (required)
  --agent TEXT   Agent ID (required)
  --expires TEXT Expiration: YYYY-MM-DD or "30d", "90d"
  --scopes TEXT  Permission scopes (can repeat)
```

**Example:**
```bash
genai-obs api-keys create \
    --name "Production Key" \
    --agent my-agent \
    --expires 90d \
    --scopes write:events \
    --scopes read:traces
```

Output:
```
✓ API key created successfully

IMPORTANT: Save this key now. It won't be shown again!

API Key: gobs_1234567890abcdef...
Key ID: abc123-def456
Prefix: gobs_123
```

### Revoke Key

```bash
genai-obs api-keys revoke KEY_ID [OPTIONS]

Options:
  --force  Skip confirmation
```

### Rotate Key

```bash
genai-obs api-keys rotate KEY_ID [OPTIONS]

Options:
  --grace-period INT  Hours to keep old key active (default: 24)
```

### Test Key

```bash
genai-obs api-keys test [OPTIONS]

Options:
  --key TEXT  API key to test (uses configured key if not provided)
```

---

## Metrics

View metrics and analytics.

### Summary

```bash
genai-obs metrics summary [OPTIONS]

Options:
  --agent TEXT   Filter by agent ID
  --period TEXT  Time period: 1h, 24h, 7d, 30d (default: 24h)
```

**Example output:**
```
==================================================
Metrics Summary (24h)
==================================================

Traces
  Total Traces: 15,234
  Success Rate: 98.5%
  Error Rate: 1.5%

Latency
  P50: 234ms
  P95: 1.2s
  P99: 3.5s

Token Usage
  Total Tokens: 2.3M
  Prompt Tokens: 1.8M
  Completion Tokens: 500K

Cost
  Total Cost: $45.67
  Avg Cost/Trace: $0.003
```

### Token Usage

```bash
genai-obs metrics tokens [OPTIONS]

Options:
  --agent TEXT    Filter by agent ID
  --model TEXT    Filter by model
  --period TEXT   Time period (default: 24h)
  --group-by TEXT Group by: agent, model, hour, day
```

### Latency

```bash
genai-obs metrics latency [OPTIONS]

Options:
  --agent TEXT    Filter by agent ID
  --period TEXT   Time period (default: 24h)
  --interval TEXT Aggregation interval (default: 1h)
```

### Error Breakdown

```bash
genai-obs metrics errors [OPTIONS]

Options:
  --agent TEXT  Filter by agent ID
  --period TEXT Time period (default: 24h)
  --top INT     Number of top error types (default: 10)
```

### Cost Breakdown

```bash
genai-obs metrics cost [OPTIONS]

Options:
  --period TEXT   Time period (default: 30d)
  --group-by TEXT Group by: agent, team, project, cost_center, day
```

### Tool Usage

```bash
genai-obs metrics tools [OPTIONS]

Options:
  --agent TEXT  Filter by agent ID
  --period TEXT Time period (default: 24h)
```

---

## Output Formats

### Table (default)

```bash
genai-obs agents list
```

```
AGENT_ID        NAME              FRAMEWORK   ENVIRONMENT  STATUS
-----------     ---------------   ----------  -----------  -------
my-agent-001    My First Agent    langchain   prod         active
my-agent-002    Test Agent        crewai      dev          active
```

### JSON

```bash
genai-obs agents list -o json
```

```json
[
  {
    "agent_id": "my-agent-001",
    "name": "My First Agent",
    "framework": "langchain",
    "environment": "prod",
    "is_active": true
  }
]
```

### Text

```bash
genai-obs agents get my-agent-001 -o text
```

```
agent_id: my-agent-001
name: My First Agent
framework: langchain
environment: prod
is_active: Yes
created_at: 2024-01-15 10:30:00
```

---

## Shell Completion

### Bash

```bash
# Add to ~/.bashrc
eval "$(_GENAI_OBS_COMPLETE=bash_source genai-obs)"
```

### Zsh

```bash
# Add to ~/.zshrc
eval "$(_GENAI_OBS_COMPLETE=zsh_source genai-obs)"
```

### Fish

```fish
# Add to ~/.config/fish/completions/genai-obs.fish
eval (env _GENAI_OBS_COMPLETE=fish_source genai-obs)
```

---

## Troubleshooting

### Connection Errors

```bash
# Test connectivity
genai-obs status

# Check with verbose output
genai-obs -v agents list
```

### Authentication Errors

```bash
# Validate API key
genai-obs api-keys test

# Check configured endpoint
genai-obs status
```

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Invalid/expired API key | Run `genai-obs configure` |
| `Connection refused` | Wrong endpoint | Check `GENAI_OBS_ENDPOINT` |
| `429 Rate Limited` | Too many requests | Wait and retry |
| `Timeout` | Slow network/API | Increase timeout in config |
