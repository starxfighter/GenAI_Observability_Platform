-- GenAI Observability Platform - Initial Database Schema
-- PostgreSQL (Aurora PostgreSQL compatible)

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- ============================================================
-- CORE ENTITIES
-- ============================================================

-- Teams table
CREATE TABLE teams (
    team_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cost_center VARCHAR(100),
    slack_channel VARCHAR(100),
    email_distribution_list VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_teams_name ON teams(name);
CREATE INDEX idx_teams_cost_center ON teams(cost_center);

-- Projects table
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID NOT NULL REFERENCES teams(team_id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    environment VARCHAR(50) DEFAULT 'dev',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(team_id, name)
);

CREATE INDEX idx_projects_team ON projects(team_id);

-- Users table (synced from Cognito)
CREATE TABLE users (
    user_id UUID PRIMARY KEY,  -- Cognito sub
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    team_id UUID REFERENCES teams(team_id),
    role VARCHAR(50) DEFAULT 'viewer',  -- admin, team_admin, developer, viewer
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_team ON users(team_id);

-- Agents table
CREATE TABLE agents (
    agent_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    team_id UUID REFERENCES teams(team_id),
    project_id UUID REFERENCES projects(project_id),
    cost_center VARCHAR(100),
    environment VARCHAR(50) DEFAULT 'dev',
    framework VARCHAR(100),  -- langchain, crewai, custom, etc.
    version VARCHAR(50),
    llm_config JSONB,  -- Default LLM configuration
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    registered_by UUID REFERENCES users(user_id),
    is_active BOOLEAN DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_agents_team ON agents(team_id);
CREATE INDEX idx_agents_project ON agents(project_id);
CREATE INDEX idx_agents_cost_center ON agents(cost_center);
CREATE INDEX idx_agents_framework ON agents(framework);

-- API Keys table
CREATE TABLE api_keys (
    key_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of the key
    key_prefix VARCHAR(10) NOT NULL,  -- First 8 chars for identification
    name VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) REFERENCES agents(agent_id),
    team_id UUID REFERENCES teams(team_id),
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    scopes JSONB DEFAULT '["write:events", "read:traces"]'::jsonb,
    rate_limit_per_minute INTEGER DEFAULT 1000,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_agent ON api_keys(agent_id);
CREATE INDEX idx_api_keys_team ON api_keys(team_id);

-- ============================================================
-- ALERTING
-- ============================================================

-- Alert rules table
CREATE TABLE alert_rules (
    rule_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_id VARCHAR(255) REFERENCES agents(agent_id),
    team_id UUID REFERENCES teams(team_id),
    rule_type VARCHAR(50) NOT NULL,  -- error_rate, latency, token_usage, anomaly, custom
    conditions JSONB NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',  -- critical, high, medium, low, info
    is_enabled BOOLEAN DEFAULT TRUE,
    cooldown_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(user_id)
);

CREATE INDEX idx_alert_rules_agent ON alert_rules(agent_id);
CREATE INDEX idx_alert_rules_team ON alert_rules(team_id);
CREATE INDEX idx_alert_rules_type ON alert_rules(rule_type);

-- Notification routes table
CREATE TABLE notification_routes (
    route_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID REFERENCES alert_rules(rule_id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL,  -- slack, pagerduty, teams, email
    channel_config JSONB NOT NULL,  -- Channel-specific configuration
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notification_routes_rule ON notification_routes(rule_id);

-- Alert history table
CREATE TABLE alert_history (
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID REFERENCES alert_rules(rule_id),
    agent_id VARCHAR(255),
    trace_id VARCHAR(255),
    severity VARCHAR(20) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    fingerprint VARCHAR(64),  -- For deduplication
    status VARCHAR(20) DEFAULT 'open',  -- open, acknowledged, resolved
    triggered_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by UUID REFERENCES users(user_id),
    resolved_by UUID REFERENCES users(user_id),
    metrics JSONB,
    investigation JSONB,  -- LLM investigation results
    notification_results JSONB
);

CREATE INDEX idx_alert_history_rule ON alert_history(rule_id);
CREATE INDEX idx_alert_history_agent ON alert_history(agent_id);
CREATE INDEX idx_alert_history_status ON alert_history(status);
CREATE INDEX idx_alert_history_severity ON alert_history(severity);
CREATE INDEX idx_alert_history_fingerprint ON alert_history(fingerprint);
CREATE INDEX idx_alert_history_triggered ON alert_history(triggered_at DESC);

-- ============================================================
-- ERROR PATTERNS (for LLM Investigation)
-- ============================================================

-- Error patterns master table
CREATE TABLE error_patterns (
    error_fingerprint VARCHAR(64) PRIMARY KEY,
    agent_id VARCHAR(255),
    event_type VARCHAR(100),
    error_type VARCHAR(255),
    sample_error_message TEXT,
    occurrence_count INTEGER DEFAULT 1,
    first_occurrence TIMESTAMP WITH TIME ZONE,
    last_occurrence TIMESTAMP WITH TIME ZONE,
    resolution_status VARCHAR(50) DEFAULT 'unresolved',  -- unresolved, investigating, resolved
    resolution_notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_error_patterns_agent ON error_patterns(agent_id);
CREATE INDEX idx_error_patterns_status ON error_patterns(resolution_status);
CREATE INDEX idx_error_patterns_last_occurrence ON error_patterns(last_occurrence DESC);

-- Error patterns daily aggregation
CREATE TABLE error_patterns_daily (
    id SERIAL PRIMARY KEY,
    error_fingerprint VARCHAR(64),
    agent_id VARCHAR(255),
    event_type VARCHAR(100),
    error_type VARCHAR(255),
    sample_error_message TEXT,
    occurrence_count INTEGER,
    frequency_percentage DECIMAL(5,2),
    affected_trace_count INTEGER,
    affected_models_list TEXT,
    first_seen TIMESTAMP WITH TIME ZONE,
    last_seen TIMESTAMP WITH TIME ZONE,
    date DATE NOT NULL,
    resolution_status VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_error_patterns_daily_date ON error_patterns_daily(date);
CREATE INDEX idx_error_patterns_daily_agent ON error_patterns_daily(agent_id, date);
CREATE INDEX idx_error_patterns_daily_fingerprint ON error_patterns_daily(error_fingerprint);

-- Error trends hourly
CREATE TABLE error_trends_hourly (
    id SERIAL PRIMARY KEY,
    hour TIMESTAMP WITH TIME ZONE NOT NULL,
    error_type VARCHAR(255),
    error_count INTEGER,
    affected_agents INTEGER,
    affected_traces INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_error_trends_hourly_hour ON error_trends_hourly(hour);
CREATE INDEX idx_error_trends_hourly_date ON error_trends_hourly(date);

-- ============================================================
-- TOKEN & COST ANALYTICS
-- ============================================================

-- Token usage hourly
CREATE TABLE token_usage_hourly (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    hour TIMESTAMP WITH TIME ZONE NOT NULL,
    total_prompt_tokens BIGINT,
    total_completion_tokens BIGINT,
    total_tokens BIGINT,
    request_count INTEGER,
    avg_latency_ms DECIMAL(10,2),
    max_latency_ms INTEGER,
    min_latency_ms INTEGER,
    estimated_cost_usd DECIMAL(10,4),
    process_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_token_usage_hourly_agent ON token_usage_hourly(agent_id, hour);
CREATE INDEX idx_token_usage_hourly_model ON token_usage_hourly(model, hour);
CREATE INDEX idx_token_usage_hourly_date ON token_usage_hourly(process_date);

-- Token usage daily
CREATE TABLE token_usage_daily (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    model VARCHAR(255),
    date DATE NOT NULL,
    total_prompt_tokens BIGINT,
    total_completion_tokens BIGINT,
    total_tokens BIGINT,
    total_requests INTEGER,
    total_cost_usd DECIMAL(10,4),
    avg_latency_ms DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, model, date)
);

CREATE INDEX idx_token_usage_daily_agent ON token_usage_daily(agent_id, date);
CREATE INDEX idx_token_usage_daily_date ON token_usage_daily(date);

-- Cost by agent daily
CREATE TABLE cost_by_agent_daily (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    team_id UUID,
    project_id UUID,
    cost_center VARCHAR(100),
    model VARCHAR(255),
    total_cost_usd DECIMAL(10,4),
    total_prompt_tokens BIGINT,
    total_completion_tokens BIGINT,
    request_count INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cost_by_agent_daily_agent ON cost_by_agent_daily(agent_id, date);
CREATE INDEX idx_cost_by_agent_daily_date ON cost_by_agent_daily(date);

-- Cost by team daily
CREATE TABLE cost_by_team_daily (
    id SERIAL PRIMARY KEY,
    team_id UUID NOT NULL,
    total_cost_usd DECIMAL(10,4),
    total_tokens BIGINT,
    active_agents INTEGER,
    total_requests INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(team_id, date)
);

CREATE INDEX idx_cost_by_team_daily_team ON cost_by_team_daily(team_id, date);
CREATE INDEX idx_cost_by_team_daily_date ON cost_by_team_daily(date);

-- Cost by project daily
CREATE TABLE cost_by_project_daily (
    id SERIAL PRIMARY KEY,
    project_id UUID NOT NULL,
    total_cost_usd DECIMAL(10,4),
    total_tokens BIGINT,
    active_agents INTEGER,
    total_requests INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, date)
);

CREATE INDEX idx_cost_by_project_daily_project ON cost_by_project_daily(project_id, date);

-- Cost by cost center daily
CREATE TABLE cost_by_cost_center_daily (
    id SERIAL PRIMARY KEY,
    cost_center VARCHAR(100) NOT NULL,
    total_cost_usd DECIMAL(10,4),
    total_tokens BIGINT,
    active_agents INTEGER,
    active_teams INTEGER,
    total_requests INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(cost_center, date)
);

CREATE INDEX idx_cost_by_cost_center_daily_cc ON cost_by_cost_center_daily(cost_center, date);

-- Cost budgets table
CREATE TABLE cost_budgets (
    budget_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cost_center VARCHAR(100) NOT NULL UNIQUE,
    monthly_budget DECIMAL(10,2) NOT NULL,
    alert_threshold DECIMAL(3,2) DEFAULT 0.80,  -- Alert at 80% of budget
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Cost alerts
CREATE TABLE cost_alerts (
    id SERIAL PRIMARY KEY,
    cost_center VARCHAR(100) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,
    mtd_cost DECIMAL(10,4),
    monthly_budget DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- TOOL ANALYTICS
-- ============================================================

-- Tool usage hourly
CREATE TABLE tool_usage_hourly (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    hour TIMESTAMP WITH TIME ZONE NOT NULL,
    invocation_count INTEGER,
    success_count INTEGER,
    error_count INTEGER,
    avg_duration_ms DECIMAL(10,2),
    max_duration_ms INTEGER,
    min_duration_ms INTEGER,
    stddev_duration_ms DECIMAL(10,2),
    success_rate DECIMAL(5,4),
    process_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tool_usage_hourly_agent ON tool_usage_hourly(agent_id, hour);
CREATE INDEX idx_tool_usage_hourly_tool ON tool_usage_hourly(tool_name, hour);

-- Tool performance daily
CREATE TABLE tool_performance_daily (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    tool_name VARCHAR(255) NOT NULL,
    total_invocations INTEGER,
    total_successes INTEGER,
    total_errors INTEGER,
    avg_duration_ms DECIMAL(10,2),
    p50_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    p99_duration_ms INTEGER,
    success_rate DECIMAL(5,4),
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, tool_name, date)
);

CREATE INDEX idx_tool_performance_daily_agent ON tool_performance_daily(agent_id, date);
CREATE INDEX idx_tool_performance_daily_tool ON tool_performance_daily(tool_name, date);

-- Tool transitions (sequence analysis)
CREATE TABLE tool_transitions (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    from_tool VARCHAR(255) NOT NULL,
    to_tool VARCHAR(255) NOT NULL,
    transition_count INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tool_transitions_agent ON tool_transitions(agent_id, date);

-- ============================================================
-- TRACE ARCHIVE (Cold Storage Analytics)
-- ============================================================

-- Traces archive table (populated by Glue ETL)
CREATE TABLE traces_archive (
    trace_id VARCHAR(255) PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    root_span_name VARCHAR(500),
    start_time TIMESTAMP WITH TIME ZONE,
    end_time TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    status VARCHAR(50),
    event_count INTEGER,
    llm_call_count INTEGER,
    tool_call_count INTEGER,
    total_prompt_tokens BIGINT,
    total_completion_tokens BIGINT,
    total_tokens BIGINT,
    error_count INTEGER,
    models_used_str TEXT,
    tools_used_str TEXT,
    errors_json JSONB,
    full_trace_json JSONB,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_traces_archive_agent ON traces_archive(agent_id, date);
CREATE INDEX idx_traces_archive_date ON traces_archive(date);
CREATE INDEX idx_traces_archive_status ON traces_archive(status);
CREATE INDEX idx_traces_archive_duration ON traces_archive(duration_ms DESC);

-- Trace statistics daily
CREATE TABLE trace_statistics_daily (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL,
    total_traces INTEGER,
    successful_traces INTEGER,
    failed_traces INTEGER,
    avg_duration_ms DECIMAL(10,2),
    p50_duration_ms INTEGER,
    p95_duration_ms INTEGER,
    p99_duration_ms INTEGER,
    avg_events_per_trace DECIMAL(5,2),
    avg_llm_calls_per_trace DECIMAL(5,2),
    avg_tool_calls_per_trace DECIMAL(5,2),
    total_tokens BIGINT,
    success_rate DECIMAL(5,4),
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, date)
);

CREATE INDEX idx_trace_statistics_daily_agent ON trace_statistics_daily(agent_id, date);
CREATE INDEX idx_trace_statistics_daily_date ON trace_statistics_daily(date);

-- Trace anomalies (slow traces, etc.)
CREATE TABLE trace_anomalies (
    id SERIAL PRIMARY KEY,
    trace_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    anomaly_type VARCHAR(50) NOT NULL,  -- slow_trace, high_token_usage, many_errors
    duration_ms INTEGER,
    llm_call_count INTEGER,
    tool_call_count INTEGER,
    error_count INTEGER,
    date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_trace_anomalies_agent ON trace_anomalies(agent_id, date);
CREATE INDEX idx_trace_anomalies_type ON trace_anomalies(anomaly_type);

-- ============================================================
-- AUDIT LOG
-- ============================================================

CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at DESC);

-- ============================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to relevant tables
CREATE TRIGGER update_teams_updated_at BEFORE UPDATE ON teams FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_alert_rules_updated_at BEFORE UPDATE ON alert_rules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_cost_budgets_updated_at BEFORE UPDATE ON cost_budgets FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- VIEWS
-- ============================================================

-- Agent overview view
CREATE VIEW agent_overview AS
SELECT
    a.agent_id,
    a.name,
    a.description,
    a.framework,
    a.environment,
    t.name AS team_name,
    p.name AS project_name,
    a.cost_center,
    a.is_active,
    a.created_at,
    (SELECT COUNT(*) FROM api_keys ak WHERE ak.agent_id = a.agent_id AND ak.is_active = TRUE) AS active_api_keys
FROM agents a
LEFT JOIN teams t ON a.team_id = t.team_id
LEFT JOIN projects p ON a.project_id = p.project_id;

-- Cost summary view
CREATE VIEW cost_summary AS
SELECT
    cc.cost_center,
    cc.date,
    cc.total_cost_usd,
    cc.total_tokens,
    cc.active_agents,
    cb.monthly_budget,
    CASE
        WHEN cb.monthly_budget IS NOT NULL
        THEN (SELECT SUM(total_cost_usd) FROM cost_by_cost_center_daily WHERE cost_center = cc.cost_center AND date >= DATE_TRUNC('month', cc.date))
        ELSE NULL
    END AS mtd_cost,
    CASE
        WHEN cb.monthly_budget IS NOT NULL
        THEN (SELECT SUM(total_cost_usd) FROM cost_by_cost_center_daily WHERE cost_center = cc.cost_center AND date >= DATE_TRUNC('month', cc.date)) / cb.monthly_budget * 100
        ELSE NULL
    END AS budget_utilization_pct
FROM cost_by_cost_center_daily cc
LEFT JOIN cost_budgets cb ON cc.cost_center = cb.cost_center;

-- ============================================================
-- INITIAL DATA
-- ============================================================

-- Insert default team
INSERT INTO teams (name, description, cost_center) VALUES
('Platform Team', 'GenAI Observability Platform Team', 'PLATFORM-001');

-- Insert admin user placeholder (will be populated from Cognito)
-- INSERT INTO users (user_id, email, name, role) VALUES
-- (uuid_generate_v4(), 'admin@example.com', 'Admin User', 'admin');
