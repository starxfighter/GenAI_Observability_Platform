import { useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { Fragment } from 'react'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import { Card, CardHeader, Table, Pagination, SeverityBadge, StatusBadge } from '../components'
import { TimeRangeSelector } from '../components/TimeRangeSelector'
import { useAlerts } from '../lib/hooks'
import { formatRelativeTime, formatDate } from '../lib/utils'
import { TimeRange, Alert, AlertFilters } from '../types'

export default function Alerts() {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h')
  const [page, setPage] = useState(1)
  const [filters, setFilters] = useState<AlertFilters>({})
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const { data: alerts, isLoading, mutate } = useAlerts(
    { ...filters, status: statusFilter !== 'all' ? statusFilter : undefined },
    page,
    20
  )

  // Demo data
  const demoAlerts: Alert[] = [
    {
      alert_id: 'alert-001',
      agent_id: 'customer-support-bot',
      anomaly_type: 'high_error_rate',
      severity: 'critical',
      status: 'open',
      timestamp: new Date(Date.now() - 1800000).toISOString(),
      message: 'Error rate exceeded 10% threshold',
      metrics: { error_rate: 0.15, error_count: 45, threshold: 0.1 },
      investigation: {
        investigation_id: 'inv-001',
        agent_id: 'customer-support-bot',
        anomaly_type: 'high_error_rate',
        severity: 'critical',
        timestamp: new Date(Date.now() - 1700000).toISOString(),
        root_cause: 'API rate limiting from downstream service causing cascading failures',
        impact: 'Approximately 15% of customer requests are failing with timeout errors',
        remediation_steps: [
          'Implement circuit breaker pattern for downstream API calls',
          'Add retry logic with exponential backoff',
          'Increase rate limit quota with vendor',
        ],
        prevention: 'Consider implementing request queuing and caching layer',
        resolution_status: 'investigating',
      },
    },
    {
      alert_id: 'alert-002',
      agent_id: 'data-analysis-agent',
      anomaly_type: 'high_latency',
      severity: 'warning',
      status: 'acknowledged',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      message: 'Average latency exceeded 5000ms threshold',
      metrics: { avg_latency_ms: 6500, threshold_ms: 5000, sample_count: 150 },
    },
    {
      alert_id: 'alert-003',
      agent_id: 'content-generator',
      anomaly_type: 'token_spike',
      severity: 'warning',
      status: 'open',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      message: 'Token usage 3x higher than normal',
      metrics: { tokens_used: 450000, normal_tokens: 150000 },
    },
    {
      alert_id: 'alert-004',
      agent_id: 'code-assistant',
      anomaly_type: 'high_error_rate',
      severity: 'critical',
      status: 'resolved',
      timestamp: new Date(Date.now() - 86400000).toISOString(),
      message: 'Error rate exceeded 10% threshold',
      metrics: { error_rate: 0.12, error_count: 23 },
    },
    {
      alert_id: 'alert-005',
      agent_id: 'research-agent',
      anomaly_type: 'cost_anomaly',
      severity: 'info',
      status: 'open',
      timestamp: new Date(Date.now() - 43200000).toISOString(),
      message: 'Daily cost 50% higher than average',
      metrics: { daily_cost: 75.0, avg_daily_cost: 50.0 },
    },
  ]

  const displayAlerts = alerts?.items ?? demoAlerts
  const filteredAlerts = statusFilter === 'all'
    ? displayAlerts
    : displayAlerts.filter((a) => a.status === statusFilter)

  const columns = [
    {
      key: 'severity',
      header: 'Severity',
      render: (alert: Alert) => <SeverityBadge severity={alert.severity} />,
      className: 'w-24',
    },
    {
      key: 'anomaly_type',
      header: 'Type',
      render: (alert: Alert) => (
        <span className="text-sm font-medium text-gray-900">
          {alert.anomaly_type.replace(/_/g, ' ')}
        </span>
      ),
    },
    {
      key: 'agent_id',
      header: 'Agent',
      render: (alert: Alert) => (
        <span className="text-sm text-gray-600">{alert.agent_id}</span>
      ),
    },
    {
      key: 'message',
      header: 'Message',
      render: (alert: Alert) => (
        <span className="text-sm text-gray-600 truncate max-w-xs block">
          {alert.message}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (alert: Alert) => <StatusBadge status={alert.status} />,
      className: 'w-28',
    },
    {
      key: 'timestamp',
      header: 'Time',
      render: (alert: Alert) => (
        <span className="text-sm text-gray-500">{formatRelativeTime(alert.timestamp)}</span>
      ),
      className: 'w-32',
    },
  ]

  const handleAcknowledge = async (alert: Alert) => {
    // In a real app, this would call the API
    console.log('Acknowledging alert:', alert.alert_id)
    setSelectedAlert(null)
    mutate()
  }

  const handleResolve = async (alert: Alert) => {
    // In a real app, this would call the API
    console.log('Resolving alert:', alert.alert_id)
    setSelectedAlert(null)
    mutate()
  }

  // Stats
  const stats = {
    total: displayAlerts.length,
    critical: displayAlerts.filter((a) => a.severity === 'critical' && a.status !== 'resolved').length,
    warning: displayAlerts.filter((a) => a.severity === 'warning' && a.status !== 'resolved').length,
    open: displayAlerts.filter((a) => a.status === 'open').length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Alerts</h1>
          <p className="text-sm text-gray-500 mt-1">
            Monitor and manage alerts from your agents
          </p>
        </div>
        <div className="w-48">
          <TimeRangeSelector value={timeRange} onChange={setTimeRange} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-sm text-gray-500">Total Alerts</p>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Critical</p>
          <p className="text-2xl font-bold text-red-600">{stats.critical}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Warnings</p>
          <p className="text-2xl font-bold text-yellow-600">{stats.warning}</p>
        </Card>
        <Card className="p-4">
          <p className="text-sm text-gray-500">Open</p>
          <p className="text-2xl font-bold text-blue-600">{stats.open}</p>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-md">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search alerts..."
              className="input pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">Status:</span>
            {['all', 'open', 'acknowledged', 'resolved'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                  statusFilter === status
                    ? 'bg-primary-100 text-primary-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Alerts Table */}
      <Table
        columns={columns}
        data={filteredAlerts}
        loading={isLoading}
        keyExtractor={(alert) => alert.alert_id}
        onRowClick={(alert) => setSelectedAlert(alert)}
        emptyMessage="No alerts found"
      />

      {/* Pagination */}
      {(alerts?.total ?? filteredAlerts.length) > 20 && (
        <Pagination
          page={page}
          pageSize={20}
          total={alerts?.total ?? filteredAlerts.length}
          onPageChange={setPage}
        />
      )}

      {/* Alert Detail Modal */}
      <AlertDetailModal
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
        onAcknowledge={handleAcknowledge}
        onResolve={handleResolve}
      />
    </div>
  )
}

interface AlertDetailModalProps {
  alert: Alert | null
  onClose: () => void
  onAcknowledge: (alert: Alert) => void
  onResolve: (alert: Alert) => void
}

function AlertDetailModal({ alert, onClose, onAcknowledge, onResolve }: AlertDetailModalProps) {
  if (!alert) return null

  return (
    <Transition show={!!alert} as={Fragment}>
      <Dialog onClose={onClose} className="relative z-50">
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/30" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-2xl bg-white rounded-xl shadow-xl">
                <div className="flex items-center justify-between p-6 border-b">
                  <div className="flex items-center gap-3">
                    <SeverityBadge severity={alert.severity} />
                    <Dialog.Title className="text-lg font-semibold">
                      {alert.anomaly_type.replace(/_/g, ' ')}
                    </Dialog.Title>
                  </div>
                  <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
                    <XMarkIcon className="w-5 h-5" />
                  </button>
                </div>

                <div className="p-6 space-y-6">
                  {/* Alert Info */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Agent</p>
                      <p className="text-sm font-medium">{alert.agent_id}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Status</p>
                      <StatusBadge status={alert.status} />
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Triggered</p>
                      <p className="text-sm">{formatDate(alert.timestamp)}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Alert ID</p>
                      <p className="text-sm font-mono">{alert.alert_id}</p>
                    </div>
                  </div>

                  {/* Message */}
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Message</p>
                    <p className="text-sm">{alert.message}</p>
                  </div>

                  {/* Metrics */}
                  {alert.metrics && (
                    <div>
                      <p className="text-sm text-gray-500 mb-2">Metrics</p>
                      <div className="bg-gray-50 rounded-lg p-4">
                        <div className="grid grid-cols-3 gap-4">
                          {Object.entries(alert.metrics).map(([key, value]) => (
                            <div key={key}>
                              <p className="text-xs text-gray-500">{key.replace(/_/g, ' ')}</p>
                              <p className="text-sm font-medium">{value}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Investigation */}
                  {alert.investigation && (
                    <div>
                      <p className="text-sm text-gray-500 mb-2">AI Investigation</p>
                      <div className="bg-blue-50 rounded-lg p-4 space-y-4">
                        <div>
                          <p className="text-xs font-medium text-blue-700 mb-1">Root Cause</p>
                          <p className="text-sm text-blue-900">{alert.investigation.root_cause}</p>
                        </div>
                        {alert.investigation.impact && (
                          <div>
                            <p className="text-xs font-medium text-blue-700 mb-1">Impact</p>
                            <p className="text-sm text-blue-900">{alert.investigation.impact}</p>
                          </div>
                        )}
                        {alert.investigation.remediation_steps && (
                          <div>
                            <p className="text-xs font-medium text-blue-700 mb-1">Remediation Steps</p>
                            <ul className="list-disc list-inside text-sm text-blue-900">
                              {alert.investigation.remediation_steps.map((step, i) => (
                                <li key={i}>{step}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Actions */}
                {alert.status !== 'resolved' && (
                  <div className="flex items-center justify-end gap-3 p-6 border-t">
                    {alert.status === 'open' && (
                      <button
                        onClick={() => onAcknowledge(alert)}
                        className="btn-secondary flex items-center gap-2"
                      >
                        <ExclamationTriangleIcon className="w-4 h-4" />
                        Acknowledge
                      </button>
                    )}
                    <button
                      onClick={() => onResolve(alert)}
                      className="btn-primary flex items-center gap-2"
                    >
                      <CheckCircleIcon className="w-4 h-4" />
                      Resolve
                    </button>
                  </div>
                )}
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
