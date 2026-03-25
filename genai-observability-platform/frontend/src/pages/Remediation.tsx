import { useState, useEffect } from 'react'
import {
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Play,
  RotateCcw,
  ChevronRight,
  Activity,
  Zap,
  FileText,
  ExternalLink,
} from 'lucide-react'
import { useRemediationStore } from '../store'
import api, { Remediation } from '../lib/api'

// Status badge component
function StatusBadge({ status }: { status: Remediation['status'] }) {
  const statusConfig = {
    pending_approval: { color: 'bg-yellow-100 text-yellow-800', icon: Clock, label: 'Pending Approval' },
    approved: { color: 'bg-blue-100 text-blue-800', icon: CheckCircle, label: 'Approved' },
    rejected: { color: 'bg-red-100 text-red-800', icon: XCircle, label: 'Rejected' },
    in_progress: { color: 'bg-purple-100 text-purple-800', icon: Activity, label: 'In Progress' },
    completed: { color: 'bg-green-100 text-green-800', icon: CheckCircle, label: 'Completed' },
    failed: { color: 'bg-red-100 text-red-800', icon: AlertTriangle, label: 'Failed' },
    rolled_back: { color: 'bg-gray-100 text-gray-800', icon: RotateCcw, label: 'Rolled Back' },
  }

  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${config.color}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  )
}

// Risk level badge
function RiskBadge({ level }: { level: 'low' | 'medium' | 'high' }) {
  const colors = {
    low: 'bg-green-100 text-green-700',
    medium: 'bg-yellow-100 text-yellow-700',
    high: 'bg-red-100 text-red-700',
  }

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[level]}`}>
      {level.toUpperCase()}
    </span>
  )
}

// Action step component
function ActionStep({
  step,
  isActive,
  isCompleted,
  result,
}: {
  step: Remediation['action_plan']['actions'][0]
  isActive: boolean
  isCompleted: boolean
  result?: { status: string; error?: string }
}) {
  return (
    <div
      className={`p-4 rounded-lg border-2 transition-all ${
        isActive
          ? 'border-blue-500 bg-blue-50'
          : isCompleted
          ? result?.status === 'success'
            ? 'border-green-300 bg-green-50'
            : 'border-red-300 bg-red-50'
          : 'border-gray-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              isCompleted
                ? result?.status === 'success'
                  ? 'bg-green-500 text-white'
                  : 'bg-red-500 text-white'
                : isActive
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-600'
            }`}
          >
            {isCompleted ? (
              result?.status === 'success' ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <XCircle className="w-4 h-4" />
              )
            ) : (
              step.step
            )}
          </div>
          <div>
            <h4 className="font-medium text-gray-900">{step.description}</h4>
            <div className="flex items-center gap-3 mt-1">
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                {step.type}
              </span>
              <RiskBadge level={step.risk_level} />
              {step.automated && (
                <span className="text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded flex items-center gap-1">
                  <Zap className="w-3 h-3" /> Automated
                </span>
              )}
            </div>
            {step.success_criteria && (
              <p className="text-sm text-gray-500 mt-2">
                <strong>Success Criteria:</strong> {step.success_criteria}
              </p>
            )}
            {step.rollback_action && (
              <p className="text-sm text-gray-500 mt-1">
                <strong>Rollback:</strong> {step.rollback_action}
              </p>
            )}
            {result?.error && (
              <p className="text-sm text-red-600 mt-2 bg-red-50 p-2 rounded">
                Error: {result.error}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

// Remediation detail panel
function RemediationDetail({
  remediation,
  onClose,
  onApprove,
  onReject,
  onExecute,
  onRollback,
}: {
  remediation: Remediation
  onClose: () => void
  onApprove: () => void
  onReject: () => void
  onExecute: () => void
  onRollback: () => void
}) {
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectDialog, setShowRejectDialog] = useState(false)
  const [approvalNotes, setApprovalNotes] = useState('')

  const currentStep =
    remediation.status === 'in_progress'
      ? (remediation.execution_results?.length || 0) + 1
      : 0

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <Shield className="w-6 h-6 text-blue-600" />
              <h2 className="text-xl font-semibold text-gray-900">Remediation Plan</h2>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              ID: {remediation.remediation_id}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-2"
          >
            <XCircle className="w-5 h-5" />
          </button>
        </div>

        <div className="flex items-center gap-4 mt-4">
          <StatusBadge status={remediation.status} />
          <span className="text-sm text-gray-500">
            Agent: <span className="font-medium text-gray-700">{remediation.agent_id}</span>
          </span>
          <span className="text-sm text-gray-500">
            Severity: <span className="font-medium text-gray-700 capitalize">{remediation.severity}</span>
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Risk Assessment */}
        <div className="mb-6 p-4 bg-amber-50 rounded-lg border border-amber-200">
          <h3 className="font-medium text-amber-800 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Risk Assessment
          </h3>
          <p className="text-sm text-amber-700 mt-2">
            {remediation.action_plan.risk_assessment}
          </p>
        </div>

        {/* Prerequisites */}
        {remediation.action_plan.prerequisites && remediation.action_plan.prerequisites.length > 0 && (
          <div className="mb-6">
            <h3 className="font-medium text-gray-900 mb-2">Prerequisites</h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
              {remediation.action_plan.prerequisites.map((prereq, i) => (
                <li key={i}>{prereq}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Action Steps */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-medium text-gray-900">Action Plan</h3>
            <span className="text-sm text-gray-500">
              Est. Duration: {remediation.action_plan.estimated_duration_minutes} min
            </span>
          </div>
          <div className="space-y-3">
            {remediation.action_plan.actions.map((action) => {
              const result = remediation.execution_results?.find(
                (r) => r.step === action.step
              )
              return (
                <ActionStep
                  key={action.step}
                  step={action}
                  isActive={currentStep === action.step}
                  isCompleted={result !== undefined}
                  result={result}
                />
              )
            })}
          </div>
        </div>

        {/* Post-execution Checks */}
        {remediation.action_plan.post_execution_checks && (
          <div className="mb-6">
            <h3 className="font-medium text-gray-900 mb-2">Post-Execution Checks</h3>
            <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
              {remediation.action_plan.post_execution_checks.map((check, i) => (
                <li key={i}>{check}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Timestamps */}
        <div className="text-sm text-gray-500 space-y-1">
          <p>Created: {new Date(remediation.created_at).toLocaleString()}</p>
          {remediation.approved_at && (
            <p>
              Approved: {new Date(remediation.approved_at).toLocaleString()}
              {remediation.approved_by && ` by ${remediation.approved_by}`}
            </p>
          )}
          {remediation.executed_at && (
            <p>Executed: {new Date(remediation.executed_at).toLocaleString()}</p>
          )}
          {remediation.completed_at && (
            <p>Completed: {new Date(remediation.completed_at).toLocaleString()}</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="p-6 border-t border-gray-200 bg-gray-50">
        {remediation.status === 'pending_approval' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Approval Notes (optional)
              </label>
              <textarea
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
                rows={2}
                placeholder="Add any notes about this approval..."
              />
            </div>
            <div className="flex gap-3">
              <button
                onClick={onApprove}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <CheckCircle className="w-4 h-4" />
                Approve
              </button>
              <button
                onClick={() => setShowRejectDialog(true)}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
              >
                <XCircle className="w-4 h-4" />
                Reject
              </button>
            </div>
          </div>
        )}

        {remediation.status === 'approved' && (
          <button
            onClick={onExecute}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Play className="w-4 h-4" />
            Execute Remediation
          </button>
        )}

        {(remediation.status === 'completed' || remediation.status === 'failed') &&
          remediation.rollback_available && (
            <div className="space-y-2">
              {remediation.rollback_deadline && (
                <p className="text-sm text-gray-500 text-center">
                  Rollback available until:{' '}
                  {new Date(remediation.rollback_deadline).toLocaleString()}
                </p>
              )}
              <button
                onClick={onRollback}
                className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Rollback Changes
              </button>
            </div>
          )}

        {/* Reject Dialog */}
        {showRejectDialog && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Reject Remediation
              </h3>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                rows={3}
                placeholder="Please provide a reason for rejection..."
              />
              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => setShowRejectDialog(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    onReject()
                    setShowRejectDialog(false)
                  }}
                  disabled={!rejectReason.trim()}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                >
                  Confirm Reject
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// Demo data
const demoRemediations: Remediation[] = [
  {
    remediation_id: 'rem_001',
    investigation_id: 'inv_123',
    agent_id: 'agent_billing_processor',
    severity: 'high',
    status: 'pending_approval',
    action_plan: {
      actions: [
        {
          step: 1,
          type: 'scale_up',
          description: 'Increase billing processor replicas from 3 to 6',
          automated: true,
          risk_level: 'low',
          success_criteria: 'All new replicas healthy and accepting requests',
          rollback_action: 'Scale back down to 3 replicas',
        },
        {
          step: 2,
          type: 'configuration_change',
          description: 'Increase connection pool size from 10 to 25',
          automated: true,
          risk_level: 'medium',
          success_criteria: 'Connection pool metrics stable',
          rollback_action: 'Revert connection pool to 10',
        },
        {
          step: 3,
          type: 'cache_clear',
          description: 'Clear stale billing cache entries',
          automated: true,
          risk_level: 'low',
          success_criteria: 'Cache hit rate recovers within 5 minutes',
        },
      ],
      estimated_duration_minutes: 15,
      risk_assessment:
        'Medium risk - scaling operations are reversible. Connection pool change may temporarily increase latency during warmup.',
      prerequisites: [
        'Verify billing queue backlog is manageable',
        'Confirm no active deployments in progress',
      ],
      post_execution_checks: [
        'Monitor error rate for 15 minutes',
        'Verify billing transactions processing normally',
        'Check database connection metrics',
      ],
    },
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    rollback_available: true,
    rollback_deadline: new Date(Date.now() + 1000 * 60 * 60 * 24).toISOString(),
  },
  {
    remediation_id: 'rem_002',
    investigation_id: 'inv_124',
    agent_id: 'agent_recommendation_engine',
    severity: 'medium',
    status: 'in_progress',
    action_plan: {
      actions: [
        {
          step: 1,
          type: 'restart_service',
          description: 'Rolling restart of recommendation service pods',
          automated: true,
          risk_level: 'low',
          success_criteria: 'All pods healthy after restart',
        },
        {
          step: 2,
          type: 'model_rollback',
          description: 'Rollback to previous ML model version (v2.3.1)',
          automated: false,
          risk_level: 'medium',
          success_criteria: 'Model inference latency < 100ms p99',
          rollback_action: 'Re-deploy current model v2.4.0',
        },
      ],
      estimated_duration_minutes: 20,
      risk_assessment:
        'Low risk - rolling restart has zero downtime. Model rollback is tested and verified.',
    },
    created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    approved_at: new Date(Date.now() - 1000 * 60 * 40).toISOString(),
    approved_by: 'admin@example.com',
    executed_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
    execution_results: [
      { step: 1, type: 'restart_service', status: 'success' },
    ],
    rollback_available: true,
  },
  {
    remediation_id: 'rem_003',
    investigation_id: 'inv_125',
    agent_id: 'agent_data_pipeline',
    severity: 'critical',
    status: 'completed',
    action_plan: {
      actions: [
        {
          step: 1,
          type: 'circuit_breaker',
          description: 'Enable circuit breaker for external API calls',
          automated: true,
          risk_level: 'low',
          success_criteria: 'Circuit breaker active and logging',
        },
        {
          step: 2,
          type: 'rate_limit',
          description: 'Reduce API call rate from 1000/s to 500/s',
          automated: true,
          risk_level: 'medium',
          success_criteria: 'No 429 errors from external API',
        },
      ],
      estimated_duration_minutes: 5,
      risk_assessment: 'Low risk - protective measures to prevent cascading failures.',
    },
    created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    approved_at: new Date(Date.now() - 1000 * 60 * 115).toISOString(),
    approved_by: 'ops@example.com',
    executed_at: new Date(Date.now() - 1000 * 60 * 110).toISOString(),
    completed_at: new Date(Date.now() - 1000 * 60 * 100).toISOString(),
    execution_results: [
      { step: 1, type: 'circuit_breaker', status: 'success' },
      { step: 2, type: 'rate_limit', status: 'success' },
    ],
    rollback_available: true,
    rollback_deadline: new Date(Date.now() + 1000 * 60 * 60 * 12).toISOString(),
  },
  {
    remediation_id: 'rem_004',
    investigation_id: 'inv_126',
    agent_id: 'agent_auth_service',
    severity: 'high',
    status: 'failed',
    action_plan: {
      actions: [
        {
          step: 1,
          type: 'configuration_change',
          description: 'Update JWT token expiration from 1h to 15m',
          automated: true,
          risk_level: 'high',
          success_criteria: 'New tokens issued with 15m expiry',
        },
        {
          step: 2,
          type: 'invalidate_sessions',
          description: 'Invalidate all active sessions',
          automated: false,
          risk_level: 'high',
          success_criteria: 'All users re-authenticated',
        },
      ],
      estimated_duration_minutes: 10,
      risk_assessment: 'High risk - will force all users to re-authenticate.',
    },
    created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    approved_at: new Date(Date.now() - 1000 * 60 * 175).toISOString(),
    approved_by: 'security@example.com',
    executed_at: new Date(Date.now() - 1000 * 60 * 170).toISOString(),
    execution_results: [
      { step: 1, type: 'configuration_change', status: 'success' },
      { step: 2, type: 'invalidate_sessions', status: 'failed', error: 'Redis connection timeout' },
    ],
    rollback_available: true,
  },
]

export default function RemediationPage() {
  const [remediations, setRemediations] = useState<Remediation[]>([])
  const [selectedRemediation, setSelectedRemediation] = useState<Remediation | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | Remediation['status']>('all')

  useEffect(() => {
    loadRemediations()
  }, [])

  const loadRemediations = async () => {
    setIsLoading(true)
    try {
      const response = await api.getRemediations()
      setRemediations(response.items)
    } catch (error) {
      console.log('Using demo remediation data')
      setRemediations(demoRemediations)
    } finally {
      setIsLoading(false)
    }
  }

  const handleApprove = async (id: string) => {
    try {
      const updated = await api.approveRemediation(id)
      setRemediations((prev) =>
        prev.map((r) => (r.remediation_id === id ? updated : r))
      )
      setSelectedRemediation(updated)
    } catch (error) {
      // Demo: update locally
      setRemediations((prev) =>
        prev.map((r) =>
          r.remediation_id === id
            ? { ...r, status: 'approved' as const, approved_at: new Date().toISOString() }
            : r
        )
      )
      if (selectedRemediation?.remediation_id === id) {
        setSelectedRemediation({
          ...selectedRemediation,
          status: 'approved',
          approved_at: new Date().toISOString(),
        })
      }
    }
  }

  const handleReject = async (id: string, reason: string) => {
    try {
      const updated = await api.rejectRemediation(id, reason)
      setRemediations((prev) =>
        prev.map((r) => (r.remediation_id === id ? updated : r))
      )
      setSelectedRemediation(updated)
    } catch (error) {
      // Demo: update locally
      setRemediations((prev) =>
        prev.map((r) =>
          r.remediation_id === id ? { ...r, status: 'rejected' as const } : r
        )
      )
      if (selectedRemediation?.remediation_id === id) {
        setSelectedRemediation({ ...selectedRemediation, status: 'rejected' })
      }
    }
  }

  const handleExecute = async (id: string) => {
    try {
      const updated = await api.executeRemediation(id)
      setRemediations((prev) =>
        prev.map((r) => (r.remediation_id === id ? updated : r))
      )
      setSelectedRemediation(updated)
    } catch (error) {
      // Demo: update locally
      setRemediations((prev) =>
        prev.map((r) =>
          r.remediation_id === id
            ? { ...r, status: 'in_progress' as const, executed_at: new Date().toISOString() }
            : r
        )
      )
      if (selectedRemediation?.remediation_id === id) {
        setSelectedRemediation({
          ...selectedRemediation,
          status: 'in_progress',
          executed_at: new Date().toISOString(),
        })
      }
    }
  }

  const handleRollback = async (id: string) => {
    try {
      const updated = await api.rollbackRemediation(id, 'User initiated rollback')
      setRemediations((prev) =>
        prev.map((r) => (r.remediation_id === id ? updated : r))
      )
      setSelectedRemediation(updated)
    } catch (error) {
      // Demo: update locally
      setRemediations((prev) =>
        prev.map((r) =>
          r.remediation_id === id ? { ...r, status: 'rolled_back' as const } : r
        )
      )
      if (selectedRemediation?.remediation_id === id) {
        setSelectedRemediation({ ...selectedRemediation, status: 'rolled_back' })
      }
    }
  }

  const filteredRemediations =
    filter === 'all'
      ? remediations
      : remediations.filter((r) => r.status === filter)

  const statusCounts = remediations.reduce(
    (acc, r) => {
      acc[r.status] = (acc[r.status] || 0) + 1
      return acc
    },
    {} as Record<string, number>
  )

  return (
    <div className="h-full flex">
      {/* Left panel - List */}
      <div className={`${selectedRemediation ? 'w-1/2' : 'w-full'} flex flex-col border-r border-gray-200`}>
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-blue-600" />
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Autonomous Remediation</h1>
                <p className="text-sm text-gray-500">AI-powered incident resolution</p>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-4 mt-6">
            <button
              onClick={() => setFilter('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'all'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              All ({remediations.length})
            </button>
            <button
              onClick={() => setFilter('pending_approval')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'pending_approval'
                  ? 'bg-yellow-500 text-white'
                  : 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100'
              }`}
            >
              Pending ({statusCounts['pending_approval'] || 0})
            </button>
            <button
              onClick={() => setFilter('in_progress')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'in_progress'
                  ? 'bg-purple-500 text-white'
                  : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
              }`}
            >
              In Progress ({statusCounts['in_progress'] || 0})
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === 'completed'
                  ? 'bg-green-500 text-white'
                  : 'bg-green-50 text-green-700 hover:bg-green-100'
              }`}
            >
              Completed ({statusCounts['completed'] || 0})
            </button>
          </div>
        </div>

        {/* List */}
        <div className="flex-1 overflow-y-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : filteredRemediations.length === 0 ? (
            <div className="text-center py-12">
              <Shield className="w-12 h-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No remediation actions found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredRemediations.map((remediation) => (
                <button
                  key={remediation.remediation_id}
                  onClick={() => setSelectedRemediation(remediation)}
                  className={`w-full text-left p-4 rounded-xl border-2 transition-all hover:shadow-md ${
                    selectedRemediation?.remediation_id === remediation.remediation_id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 bg-white hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="font-semibold text-gray-900">
                          {remediation.agent_id}
                        </span>
                        <StatusBadge status={remediation.status} />
                      </div>
                      <p className="text-sm text-gray-500 mt-1 line-clamp-2">
                        {remediation.action_plan.actions[0]?.description}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {remediation.action_plan.actions.length} steps
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {remediation.action_plan.estimated_duration_minutes} min
                        </span>
                        <span className={`capitalize ${
                          remediation.severity === 'critical' ? 'text-red-500' :
                          remediation.severity === 'high' ? 'text-orange-500' :
                          'text-yellow-500'
                        }`}>
                          {remediation.severity}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-5 h-5 text-gray-400" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right panel - Detail */}
      {selectedRemediation && (
        <div className="w-1/2">
          <RemediationDetail
            remediation={selectedRemediation}
            onClose={() => setSelectedRemediation(null)}
            onApprove={() => handleApprove(selectedRemediation.remediation_id)}
            onReject={() => handleReject(selectedRemediation.remediation_id, 'Rejected')}
            onExecute={() => handleExecute(selectedRemediation.remediation_id)}
            onRollback={() => handleRollback(selectedRemediation.remediation_id)}
          />
        </div>
      )}
    </div>
  )
}
