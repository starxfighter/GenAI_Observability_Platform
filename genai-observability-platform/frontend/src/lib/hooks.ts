import useSWR from 'swr'
import api from './api'
import type {
  Agent,
  Trace,
  Alert,
  DashboardMetrics,
  AgentMetrics,
  MetricSeries,
  PaginatedResponse,
  TraceFilters,
  AlertFilters,
  TimeRange,
} from '../types'

// SWR Configuration
const swrConfig = {
  revalidateOnFocus: false,
  dedupingInterval: 5000,
}

// Dashboard Hooks
export function useDashboardMetrics(timeRange: TimeRange) {
  return useSWR<DashboardMetrics>(
    ['dashboard-metrics', timeRange],
    () => api.getDashboardMetrics(timeRange),
    { ...swrConfig, refreshInterval: 30000 }
  )
}

export function useMetricsSeries(metric: string, timeRange: TimeRange, agentId?: string) {
  return useSWR<MetricSeries>(
    ['metrics-series', metric, timeRange, agentId],
    () => api.getMetricsSeries(metric, timeRange, agentId),
    { ...swrConfig, refreshInterval: 30000 }
  )
}

// Agent Hooks
export function useAgents(page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<Agent>>(
    ['agents', page, pageSize],
    () => api.getAgents(page, pageSize),
    swrConfig
  )
}

export function useAgent(agentId: string | undefined) {
  return useSWR<Agent>(
    agentId ? ['agent', agentId] : null,
    () => api.getAgent(agentId!),
    swrConfig
  )
}

export function useAgentMetrics(agentId: string | undefined, timeRange: TimeRange) {
  return useSWR<AgentMetrics>(
    agentId ? ['agent-metrics', agentId, timeRange] : null,
    () => api.getAgentMetrics(agentId!, timeRange),
    { ...swrConfig, refreshInterval: 30000 }
  )
}

// Trace Hooks
export function useTraces(filters: TraceFilters = {}, page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<Trace>>(
    ['traces', filters, page, pageSize],
    () => api.getTraces(filters, page, pageSize),
    swrConfig
  )
}

export function useTrace(traceId: string | undefined) {
  return useSWR<Trace>(
    traceId ? ['trace', traceId] : null,
    () => api.getTrace(traceId!),
    swrConfig
  )
}

// Alert Hooks
export function useAlerts(filters: AlertFilters = {}, page = 1, pageSize = 20) {
  return useSWR<PaginatedResponse<Alert>>(
    ['alerts', filters, page, pageSize],
    () => api.getAlerts(filters, page, pageSize),
    { ...swrConfig, refreshInterval: 15000 }
  )
}

export function useAlert(alertId: string | undefined) {
  return useSWR<Alert>(
    alertId ? ['alert', alertId] : null,
    () => api.getAlert(alertId!),
    swrConfig
  )
}

// Health Hook
export function useHealth() {
  return useSWR(
    'health',
    () => api.getHealth(),
    { ...swrConfig, refreshInterval: 60000 }
  )
}
