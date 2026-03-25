-- GenAI Observability Platform - LLM Investigation Tables
-- Stores investigation results and historical patterns for AI-powered root cause analysis

-- ============================================================
-- LLM INVESTIGATION RESULTS
-- ============================================================

-- Investigation results table
CREATE TABLE investigation_results (
    investigation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id UUID REFERENCES alert_history(alert_id),
    trace_id VARCHAR(255),
    agent_id VARCHAR(255),

    -- Investigation input
    error_type VARCHAR(255),
    error_message TEXT,
    context_data JSONB,  -- Span data, metrics, etc.

    -- LLM analysis results
    root_cause TEXT,
    root_cause_confidence DECIMAL(3,2),  -- 0.00 to 1.00
    impact_assessment TEXT,
    recommendations JSONB,  -- Array of recommended actions

    -- Similar incidents
    similar_incidents JSONB,  -- Array of {investigation_id, similarity_score, resolution}

    -- Resolution tracking
    resolution_status VARCHAR(50) DEFAULT 'pending',  -- pending, in_progress, resolved, wont_fix
    resolution_notes TEXT,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by UUID REFERENCES users(user_id),

    -- LLM metadata
    model_used VARCHAR(100),
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    investigation_cost_usd DECIMAL(8,6),
    latency_ms INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_investigation_results_alert ON investigation_results(alert_id);
CREATE INDEX idx_investigation_results_trace ON investigation_results(trace_id);
CREATE INDEX idx_investigation_results_agent ON investigation_results(agent_id);
CREATE INDEX idx_investigation_results_status ON investigation_results(resolution_status);
CREATE INDEX idx_investigation_results_created ON investigation_results(created_at DESC);

-- Investigation feedback table (for improving LLM accuracy)
CREATE TABLE investigation_feedback (
    feedback_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID NOT NULL REFERENCES investigation_results(investigation_id),
    user_id UUID REFERENCES users(user_id),

    -- Feedback on root cause accuracy
    root_cause_accurate BOOLEAN,
    actual_root_cause TEXT,

    -- Feedback on recommendations
    recommendations_helpful BOOLEAN,
    applied_recommendations JSONB,  -- Which recommendations were applied

    -- Additional context
    feedback_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_investigation_feedback_investigation ON investigation_feedback(investigation_id);

-- Known resolutions table (for pattern matching)
CREATE TABLE known_resolutions (
    resolution_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    error_fingerprint VARCHAR(64),
    error_type VARCHAR(255),
    error_pattern TEXT,  -- Regex or fuzzy match pattern

    -- Resolution details
    root_cause TEXT NOT NULL,
    resolution_steps JSONB NOT NULL,  -- Array of steps
    prevention_measures JSONB,  -- How to prevent recurrence

    -- Effectiveness tracking
    times_applied INTEGER DEFAULT 0,
    success_rate DECIMAL(5,4) DEFAULT 0.0,
    avg_resolution_time_minutes INTEGER,

    -- Metadata
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_known_resolutions_fingerprint ON known_resolutions(error_fingerprint);
CREATE INDEX idx_known_resolutions_type ON known_resolutions(error_type);

-- ============================================================
-- INVESTIGATION PROMPTS & TEMPLATES
-- ============================================================

-- Investigation prompt templates
CREATE TABLE investigation_prompts (
    prompt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    prompt_type VARCHAR(50) NOT NULL,  -- root_cause, recommendation, impact, summary

    -- Prompt content
    system_prompt TEXT NOT NULL,
    user_prompt_template TEXT NOT NULL,

    -- Configuration
    model VARCHAR(100) DEFAULT 'claude-sonnet-4-20250514',
    max_tokens INTEGER DEFAULT 1024,
    temperature DECIMAL(2,1) DEFAULT 0.3,

    -- Versioning
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Default investigation prompt
INSERT INTO investigation_prompts (name, description, prompt_type, system_prompt, user_prompt_template) VALUES
(
    'Default Root Cause Analysis',
    'Standard prompt for analyzing root causes of errors in GenAI agents',
    'root_cause',
    'You are an expert at debugging GenAI agents and distributed systems. Analyze the following error information and provide a concise root cause analysis.

Focus on:
1. The immediate cause of the error
2. Contributing factors from the trace context
3. Potential systemic issues
4. Actionable recommendations

Be specific and technical. Reference span IDs and timestamps when relevant.',

    'Error Information:
- Error Type: {{error_type}}
- Error Message: {{error_message}}
- Agent: {{agent_id}}
- Trace ID: {{trace_id}}

Trace Context:
{{trace_context}}

Recent Metrics:
{{metrics}}

Similar Past Errors (last 7 days):
{{similar_errors}}

Please analyze this error and provide:
1. Root Cause (1-2 sentences)
2. Contributing Factors (bullet points)
3. Recommendations (prioritized list)
4. Prevention Measures'
);

-- ============================================================
-- INVESTIGATION ANALYTICS
-- ============================================================

-- Investigation statistics daily
CREATE TABLE investigation_statistics_daily (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_investigations INTEGER DEFAULT 0,
    auto_resolved INTEGER DEFAULT 0,  -- Resolved by matching known pattern
    manual_resolved INTEGER DEFAULT 0,
    avg_resolution_time_minutes DECIMAL(10,2),
    avg_investigation_cost_usd DECIMAL(8,6),
    total_investigation_cost_usd DECIMAL(10,4),

    -- By severity
    critical_investigations INTEGER DEFAULT 0,
    high_investigations INTEGER DEFAULT 0,
    medium_investigations INTEGER DEFAULT 0,
    low_investigations INTEGER DEFAULT 0,

    -- Accuracy metrics (from feedback)
    root_cause_accuracy_rate DECIMAL(5,4),
    recommendation_helpfulness_rate DECIMAL(5,4),

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(date)
);

CREATE INDEX idx_investigation_statistics_date ON investigation_statistics_daily(date);

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Function to find similar investigations
CREATE OR REPLACE FUNCTION find_similar_investigations(
    p_error_type VARCHAR(255),
    p_error_message TEXT,
    p_agent_id VARCHAR(255),
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    investigation_id UUID,
    error_type VARCHAR(255),
    error_message TEXT,
    root_cause TEXT,
    resolution_status VARCHAR(50),
    similarity_score DECIMAL(5,4)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ir.investigation_id,
        ir.error_type,
        ir.error_message,
        ir.root_cause,
        ir.resolution_status,
        -- Simple similarity based on error type match and message trigram similarity
        CASE
            WHEN ir.error_type = p_error_type THEN 0.5
            ELSE 0.0
        END +
        COALESCE(similarity(ir.error_message, p_error_message) * 0.5, 0)
        AS similarity_score
    FROM investigation_results ir
    WHERE ir.resolution_status = 'resolved'
    AND (ir.error_type = p_error_type OR similarity(ir.error_message, p_error_message) > 0.3)
    ORDER BY similarity_score DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to record investigation usage
CREATE OR REPLACE FUNCTION record_investigation_usage(
    p_investigation_id UUID,
    p_was_helpful BOOLEAN
)
RETURNS VOID AS $$
BEGIN
    -- Update investigation feedback stats
    UPDATE investigation_results
    SET updated_at = NOW()
    WHERE investigation_id = p_investigation_id;

    -- If there's a known resolution linked, update its stats
    UPDATE known_resolutions kr
    SET
        times_applied = times_applied + 1,
        success_rate = (success_rate * times_applied + CASE WHEN p_was_helpful THEN 1 ELSE 0 END) / (times_applied + 1),
        updated_at = NOW()
    WHERE kr.error_fingerprint IN (
        SELECT ep.error_fingerprint
        FROM error_patterns ep
        JOIN investigation_results ir ON ir.agent_id = ep.agent_id AND ir.error_type = ep.error_type
        WHERE ir.investigation_id = p_investigation_id
    );
END;
$$ LANGUAGE plpgsql;

-- Trigger to update investigation_results updated_at
CREATE TRIGGER update_investigation_results_updated_at
    BEFORE UPDATE ON investigation_results
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_known_resolutions_updated_at
    BEFORE UPDATE ON known_resolutions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_investigation_prompts_updated_at
    BEFORE UPDATE ON investigation_prompts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
