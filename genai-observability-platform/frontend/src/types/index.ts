// Agent Types
export interface Agent {
  agent_id: string
  name: string
  framework: string
  version: string
  status: 'active' | 'inactive' | 'error'
  last_seen: string
  created_at: string
  metadata?: Record<string, unknown>
}

// Trace Types
export interface Trace {
  trace_id: string
  agent_id: string
  parent_span_id?: string
  name: string
  start_time: string
  end_time?: string
  duration_ms?: number
  status: 'running' | 'completed' | 'error'
  spans: Span[]
  metadata?: Record<string, unknown>
}

export interface Span {
  span_id: string
  trace_id: string
  parent_span_id?: string
  name: string
  span_type: 'execution' | 'llm' | 'tool' | 'mcp'
  start_time: string
  end_time?: string
  duration_ms?: number
  status: 'running' | 'completed' | 'error'
  attributes?: Record<string, unknown>
  events?: SpanEvent[]
}

export interface SpanEvent {
  name: string
  timestamp: string
  attributes?: Record<string, unknown>
}

// Metrics Types
export interface MetricPoint {
  timestamp: string
  value: number
}

export interface MetricSeries {
  name: string
  data: MetricPoint[]
}

export interface AgentMetrics {
  agent_id: string
  period: string
  request_count: number
  error_count: number
  error_rate: number
  avg_latency_ms: number
  p50_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
  total_tokens: number
  total_cost: number
}

export interface DashboardMetrics {
  total_agents: number
  active_agents: number
  total_traces: number
  total_errors: number
  avg_latency_ms: number
  total_tokens: number
  total_cost: number
  period: string
}

// Alert Types
export interface Alert {
  alert_id: string
  agent_id: string
  anomaly_type: 'high_error_rate' | 'high_latency' | 'token_spike' | 'cost_anomaly'
  severity: 'critical' | 'warning' | 'info'
  status: 'open' | 'acknowledged' | 'resolved'
  timestamp: string
  message: string
  metrics?: Record<string, number>
  investigation?: Investigation
}

export interface Investigation {
  investigation_id: string
  agent_id: string
  anomaly_type: string
  severity: string
  timestamp: string
  root_cause?: string
  impact?: string
  remediation_steps?: string[]
  prevention?: string
  resolution_status: 'open' | 'investigating' | 'resolved'
  resolved_at?: string
  resolution_notes?: string
}

// Error Types
export interface ErrorEvent {
  error_id: string
  trace_id?: string
  span_id?: string
  agent_id: string
  error_type: string
  error_message: string
  stack_trace?: string
  timestamp: string
  severity: 'error' | 'warning'
}

// API Response Types
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface ApiError {
  error: string
  message: string
  details?: Record<string, unknown>
}

// Filter Types
export interface TraceFilters {
  agent_id?: string
  status?: string
  start_time?: string
  end_time?: string
  min_duration_ms?: number
  max_duration_ms?: number
}

export interface AlertFilters {
  agent_id?: string
  severity?: string
  status?: string
  anomaly_type?: string
  start_time?: string
  end_time?: string
}

// Time Range
export type TimeRange = '1h' | '6h' | '24h' | '7d' | '30d' | 'custom'

export interface TimeRangeOption {
  label: string
  value: TimeRange
}

export const TIME_RANGE_OPTIONS: TimeRangeOption[] = [
  { label: 'Last 1 hour', value: '1h' },
  { label: 'Last 6 hours', value: '6h' },
  { label: 'Last 24 hours', value: '24h' },
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
]
