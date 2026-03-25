import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  Agent,
  Trace,
  Alert,
  Investigation,
  ErrorEvent,
  DashboardMetrics,
  AgentMetrics,
  MetricSeries,
  PaginatedResponse,
  TraceFilters,
  AlertFilters,
  TimeRange,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Add request interceptor for auth
    this.client.interceptors.request.use((config) => {
      const apiKey = localStorage.getItem('api_key')
      if (apiKey) {
        config.headers['x-api-key'] = apiKey
      }
      return config
    })

    // Add response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('api_key')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Dashboard
  async getDashboardMetrics(timeRange: TimeRange): Promise<DashboardMetrics> {
    const { data } = await this.client.get('/dashboard/metrics', {
      params: { time_range: timeRange },
    })
    return data
  }

  async getMetricsSeries(
    metric: string,
    timeRange: TimeRange,
    agentId?: string
  ): Promise<MetricSeries> {
    const { data } = await this.client.get('/dashboard/series', {
      params: { metric, time_range: timeRange, agent_id: agentId },
    })
    return data
  }

  // Agents
  async getAgents(page = 1, pageSize = 20): Promise<PaginatedResponse<Agent>> {
    const { data } = await this.client.get('/agents', {
      params: { page, page_size: pageSize },
    })
    return data
  }

  async getAgent(agentId: string): Promise<Agent> {
    const { data } = await this.client.get(`/agents/${agentId}`)
    return data
  }

  async getAgentMetrics(agentId: string, timeRange: TimeRange): Promise<AgentMetrics> {
    const { data } = await this.client.get(`/agents/${agentId}/metrics`, {
      params: { time_range: timeRange },
    })
    return data
  }

  async updateAgent(agentId: string, updates: Partial<Agent>): Promise<Agent> {
    const { data } = await this.client.patch(`/agents/${agentId}`, updates)
    return data
  }

  // Traces
  async getTraces(
    filters: TraceFilters = {},
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<Trace>> {
    const { data } = await this.client.get('/traces', {
      params: { ...filters, page, page_size: pageSize },
    })
    return data
  }

  async getTrace(traceId: string): Promise<Trace> {
    const { data } = await this.client.get(`/traces/${traceId}`)
    return data
  }

  // Alerts
  async getAlerts(
    filters: AlertFilters = {},
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<Alert>> {
    const { data } = await this.client.get('/alerts', {
      params: { ...filters, page, page_size: pageSize },
    })
    return data
  }

  async getAlert(alertId: string): Promise<Alert> {
    const { data } = await this.client.get(`/alerts/${alertId}`)
    return data
  }

  async updateAlertStatus(
    alertId: string,
    status: 'acknowledged' | 'resolved',
    notes?: string
  ): Promise<Alert> {
    const { data } = await this.client.patch(`/alerts/${alertId}`, { status, notes })
    return data
  }

  // Investigations
  async getInvestigation(investigationId: string): Promise<Investigation> {
    const { data } = await this.client.get(`/investigations/${investigationId}`)
    return data
  }

  async updateInvestigation(
    investigationId: string,
    updates: Partial<Investigation>
  ): Promise<Investigation> {
    const { data } = await this.client.patch(`/investigations/${investigationId}`, updates)
    return data
  }

  // Errors
  async getErrors(
    agentId?: string,
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<ErrorEvent>> {
    const { data } = await this.client.get('/errors', {
      params: { agent_id: agentId, page, page_size: pageSize },
    })
    return data
  }

  // Health
  async getHealth(): Promise<{ status: string; components: Record<string, unknown> }> {
    const { data } = await this.client.get('/health')
    return data
  }

  // ============================================
  // Natural Language Query
  // ============================================
  async executeNLQuery(query: string, context?: Record<string, unknown>): Promise<NLQueryResponse> {
    const { data } = await this.client.post('/nlq', { query, context })
    return data
  }

  async getNLQuerySuggestions(context?: string): Promise<{ general: string[]; contextual: string[] }> {
    const { data } = await this.client.get('/nlq/suggestions', { params: { context } })
    return data
  }

  async getNLQueryHistory(limit = 20): Promise<NLQueryHistoryItem[]> {
    const { data } = await this.client.get('/nlq/history', { params: { limit } })
    return data
  }

  async saveNLQuery(name: string, query: string, description?: string, tags?: string[]): Promise<SavedNLQuery> {
    const { data } = await this.client.post('/nlq/saved', { name, query, description, tags })
    return data
  }

  async getSavedNLQueries(): Promise<SavedNLQuery[]> {
    const { data } = await this.client.get('/nlq/saved')
    return data
  }

  async deleteSavedNLQuery(queryId: string): Promise<void> {
    await this.client.delete(`/nlq/saved/${queryId}`)
  }

  async getNLQueryExamples(): Promise<Record<string, Array<{ query: string; description: string }>>> {
    const { data } = await this.client.get('/nlq/examples')
    return data
  }

  // ============================================
  // Remediation
  // ============================================
  async getRemediations(page = 1, pageSize = 20): Promise<PaginatedResponse<Remediation>> {
    const { data } = await this.client.get('/remediation', { params: { page, page_size: pageSize } })
    return data
  }

  async getRemediation(remediationId: string): Promise<Remediation> {
    const { data } = await this.client.get(`/remediation/${remediationId}`)
    return data
  }

  async createRemediation(investigationId: string): Promise<Remediation> {
    const { data } = await this.client.post('/remediation/plan', { investigation_id: investigationId })
    return data
  }

  async approveRemediation(remediationId: string, notes?: string): Promise<Remediation> {
    const { data } = await this.client.post(`/remediation/${remediationId}/approve`, { notes })
    return data
  }

  async rejectRemediation(remediationId: string, reason: string): Promise<Remediation> {
    const { data } = await this.client.post(`/remediation/${remediationId}/reject`, { reason })
    return data
  }

  async executeRemediation(remediationId: string): Promise<Remediation> {
    const { data } = await this.client.post(`/remediation/${remediationId}/execute`)
    return data
  }

  async rollbackRemediation(remediationId: string, reason: string): Promise<Remediation> {
    const { data } = await this.client.post(`/remediation/${remediationId}/rollback`, { reason })
    return data
  }

  // ============================================
  // Integrations
  // ============================================
  async getIntegrations(): Promise<Integration[]> {
    const { data } = await this.client.get('/integrations')
    return data
  }

  async getIntegration(integrationId: string): Promise<Integration> {
    const { data } = await this.client.get(`/integrations/${integrationId}`)
    return data
  }

  async createIntegration(integration: CreateIntegrationRequest): Promise<Integration> {
    const { data } = await this.client.post('/integrations', integration)
    return data
  }

  async updateIntegration(integrationId: string, updates: Partial<Integration>): Promise<Integration> {
    const { data } = await this.client.patch(`/integrations/${integrationId}`, updates)
    return data
  }

  async deleteIntegration(integrationId: string): Promise<void> {
    await this.client.delete(`/integrations/${integrationId}`)
  }

  async testIntegration(integrationId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await this.client.post(`/integrations/${integrationId}/test`)
    return data
  }

  async syncIntegration(integrationId: string): Promise<{ success: boolean; synced_at: string }> {
    const { data } = await this.client.post(`/integrations/${integrationId}/sync`)
    return data
  }

  async createExternalIssue(
    integrationId: string,
    alertId: string,
    options?: { issueType?: string; priority?: string }
  ): Promise<{ external_id: string; url: string }> {
    const { data } = await this.client.post(`/integrations/${integrationId}/issues`, {
      alert_id: alertId,
      ...options,
    })
    return data
  }

  // ============================================
  // Authentication (SSO)
  // ============================================
  async getAuthProviders(): Promise<AuthProvider[]> {
    const { data } = await this.client.get('/auth/providers')
    return data.providers
  }

  async getLoginUrl(provider: string, redirectUri: string): Promise<{ login_url: string; state: string }> {
    const { data } = await this.client.get(`/auth/login/${provider}/url`, {
      params: { redirect_uri: redirectUri },
    })
    return data
  }

  async handleAuthCallback(provider: string, params: Record<string, string>): Promise<AuthResponse> {
    const { data } = await this.client.post(`/auth/callback/${provider}`, params)
    return data
  }

  async getCurrentUser(): Promise<AuthUser> {
    const { data } = await this.client.get('/auth/me')
    return data
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout')
  }

  // ============================================
  // Settings
  // ============================================
  async getPIISettings(): Promise<PIISettings> {
    const { data } = await this.client.get('/settings/pii')
    return data
  }

  async updatePIISettings(settings: Partial<PIISettings>): Promise<PIISettings> {
    const { data } = await this.client.patch('/settings/pii', settings)
    return data
  }

  async getRegionSettings(): Promise<RegionSettings> {
    const { data } = await this.client.get('/settings/regions')
    return data
  }

  async updateRegionSettings(settings: Partial<RegionSettings>): Promise<RegionSettings> {
    const { data } = await this.client.patch('/settings/regions', settings)
    return data
  }

  async getRegionHealth(): Promise<RegionHealth[]> {
    const { data } = await this.client.get('/settings/regions/health')
    return data
  }

  async triggerFailover(targetRegion: string): Promise<{ status: string; message: string }> {
    const { data } = await this.client.post('/settings/regions/failover', { target_region: targetRegion })
    return data
  }
}

// Additional Types
export interface NLQueryResponse {
  query: string
  parsed_intent: {
    query_type: string
    intent: string
    entities: Record<string, unknown>
    aggregations: string[]
  }
  results: {
    data: unknown[]
    metadata: {
      query_type: string
      time_range: string
      executed_at: string
    }
  }
  response: string
  suggestions: string[]
}

export interface NLQueryHistoryItem {
  query_id: string
  query: string
  timestamp: string
  result_count: number
}

export interface SavedNLQuery {
  query_id: string
  name: string
  query: string
  description?: string
  created_at: string
  tags: string[]
}

export interface Remediation {
  remediation_id: string
  investigation_id: string
  agent_id: string
  severity: string
  status: 'pending_approval' | 'approved' | 'rejected' | 'in_progress' | 'completed' | 'failed' | 'rolled_back'
  action_plan: {
    actions: Array<{
      step: number
      type: string
      description: string
      parameters?: Record<string, unknown>
      automated: boolean
      risk_level: 'low' | 'medium' | 'high'
      success_criteria?: string
      rollback_action?: string
    }>
    estimated_duration_minutes: number
    risk_assessment: string
    prerequisites?: string[]
    post_execution_checks?: string[]
  }
  created_at: string
  approved_at?: string
  approved_by?: string
  executed_at?: string
  completed_at?: string
  execution_results?: Array<{
    step: number
    type: string
    status: string
    error?: string
  }>
  rollback_available: boolean
  rollback_deadline?: string
}

export interface Integration {
  integration_id: string
  type: 'jira' | 'servicenow' | 'github' | 'slack' | 'pagerduty' | 'teams'
  name: string
  enabled: boolean
  config: Record<string, unknown>
  status: 'connected' | 'disconnected' | 'error'
  last_sync?: string
  created_at: string
  error_message?: string
}

export interface CreateIntegrationRequest {
  type: Integration['type']
  name: string
  config: Record<string, unknown>
}

export interface AuthProvider {
  id: string
  name: string
  type: 'oidc' | 'saml'
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token?: string
  user: AuthUser
}

export interface AuthUser {
  user_id: string
  email: string
  name: string
  picture?: string
  provider: string
  roles: string[]
  groups: string[]
}

export interface PIISettings {
  enabled: boolean
  redact_emails: boolean
  redact_phone_numbers: boolean
  redact_ssn: boolean
  redact_credit_cards: boolean
  redact_api_keys: boolean
  custom_patterns: string[]
  redaction_strategy: 'mask' | 'hash' | 'remove'
}

export interface RegionSettings {
  primary_region: string
  secondary_region: string
  enable_failover: boolean
  routing_strategy: 'failover' | 'round_robin' | 'latency_based'
}

export interface RegionHealth {
  region_id: string
  status: 'healthy' | 'degraded' | 'unhealthy'
  latency_ms: number
  last_check: string
  services: Record<string, 'healthy' | 'unhealthy'>
}

export const api = new ApiClient()
export default api
