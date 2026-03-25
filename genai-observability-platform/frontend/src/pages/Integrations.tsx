import { useState, useEffect } from 'react'
import {
  Puzzle,
  Plus,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Settings,
  Trash2,
  ExternalLink,
  Zap,
  Clock,
} from 'lucide-react'
import api, { Integration, CreateIntegrationRequest } from '../lib/api'

// Integration type icons and colors
const integrationConfig: Record<
  Integration['type'],
  { icon: string; color: string; name: string; description: string }
> = {
  jira: {
    icon: '🎫',
    color: 'bg-blue-500',
    name: 'Jira',
    description: 'Create and sync issues with Atlassian Jira',
  },
  servicenow: {
    icon: '🔧',
    color: 'bg-green-600',
    name: 'ServiceNow',
    description: 'Sync incidents with ServiceNow ITSM',
  },
  github: {
    icon: '🐙',
    color: 'bg-gray-800',
    name: 'GitHub',
    description: 'Create issues and link to repositories',
  },
  slack: {
    icon: '💬',
    color: 'bg-purple-500',
    name: 'Slack',
    description: 'Send alerts and notifications to Slack channels',
  },
  pagerduty: {
    icon: '📟',
    color: 'bg-green-500',
    name: 'PagerDuty',
    description: 'Trigger incidents and on-call notifications',
  },
  teams: {
    icon: '👥',
    color: 'bg-indigo-600',
    name: 'Microsoft Teams',
    description: 'Send alerts to Microsoft Teams channels',
  },
}

// Status badge component
function StatusBadge({ status }: { status: Integration['status'] }) {
  const config = {
    connected: { color: 'bg-green-100 text-green-700', icon: CheckCircle, label: 'Connected' },
    disconnected: { color: 'bg-gray-100 text-gray-600', icon: XCircle, label: 'Disconnected' },
    error: { color: 'bg-red-100 text-red-700', icon: AlertTriangle, label: 'Error' },
  }

  const c = config[status]
  const Icon = c.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${c.color}`}>
      <Icon className="w-3.5 h-3.5" />
      {c.label}
    </span>
  )
}

// Integration card component
function IntegrationCard({
  integration,
  onTest,
  onSync,
  onConfigure,
  onDelete,
  onToggle,
}: {
  integration: Integration
  onTest: () => void
  onSync: () => void
  onConfigure: () => void
  onDelete: () => void
  onToggle: () => void
}) {
  const [isTesting, setIsTesting] = useState(false)
  const [isSyncing, setIsSyncing] = useState(false)

  const config = integrationConfig[integration.type]

  const handleTest = async () => {
    setIsTesting(true)
    await onTest()
    setIsTesting(false)
  }

  const handleSync = async () => {
    setIsSyncing(true)
    await onSync()
    setIsSyncing(false)
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div
            className={`w-14 h-14 rounded-xl ${config.color} flex items-center justify-center text-2xl`}
          >
            {config.icon}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-gray-900">{integration.name}</h3>
              <StatusBadge status={integration.status} />
            </div>
            <p className="text-sm text-gray-500 mt-0.5">{config.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={integration.enabled}
              onChange={onToggle}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>
      </div>

      {integration.error_message && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">{integration.error_message}</p>
        </div>
      )}

      {integration.last_sync && (
        <div className="mt-4 flex items-center gap-2 text-sm text-gray-500">
          <Clock className="w-4 h-4" />
          Last synced: {new Date(integration.last_sync).toLocaleString()}
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-2">
        <button
          onClick={handleTest}
          disabled={isTesting}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          {isTesting ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Zap className="w-4 h-4" />
          )}
          Test
        </button>
        <button
          onClick={handleSync}
          disabled={isSyncing || !integration.enabled}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
        >
          {isSyncing ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Sync
        </button>
        <button
          onClick={onConfigure}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
        >
          <Settings className="w-4 h-4" />
          Configure
        </button>
        <button
          onClick={onDelete}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors ml-auto"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// Add integration modal
function AddIntegrationModal({
  onClose,
  onAdd,
}: {
  onClose: () => void
  onAdd: (integration: CreateIntegrationRequest) => void
}) {
  const [step, setStep] = useState<'select' | 'configure'>('select')
  const [selectedType, setSelectedType] = useState<Integration['type'] | null>(null)
  const [name, setName] = useState('')
  const [config, setConfig] = useState<Record<string, string>>({})

  const configFields: Record<Integration['type'], Array<{ key: string; label: string; type: string; required: boolean }>> = {
    jira: [
      { key: 'base_url', label: 'Jira URL', type: 'url', required: true },
      { key: 'username', label: 'Username/Email', type: 'text', required: true },
      { key: 'api_token', label: 'API Token', type: 'password', required: true },
      { key: 'project_key', label: 'Default Project Key', type: 'text', required: true },
    ],
    servicenow: [
      { key: 'instance_url', label: 'Instance URL', type: 'url', required: true },
      { key: 'username', label: 'Username', type: 'text', required: true },
      { key: 'password', label: 'Password', type: 'password', required: true },
    ],
    github: [
      { key: 'token', label: 'Personal Access Token', type: 'password', required: true },
      { key: 'owner', label: 'Repository Owner', type: 'text', required: true },
      { key: 'repo', label: 'Repository Name', type: 'text', required: true },
    ],
    slack: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'url', required: true },
      { key: 'channel', label: 'Default Channel', type: 'text', required: false },
    ],
    pagerduty: [
      { key: 'api_key', label: 'API Key', type: 'password', required: true },
      { key: 'service_id', label: 'Service ID', type: 'text', required: true },
    ],
    teams: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'url', required: true },
    ],
  }

  const handleSubmit = () => {
    if (!selectedType || !name) return
    onAdd({
      type: selectedType,
      name,
      config,
    })
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              {step === 'select' ? 'Add Integration' : `Configure ${selectedType && integrationConfig[selectedType]?.name}`}
            </h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {step === 'select' ? (
            <div className="grid grid-cols-2 gap-4">
              {(Object.entries(integrationConfig) as [Integration['type'], typeof integrationConfig['jira']][]).map(
                ([type, cfg]) => (
                  <button
                    key={type}
                    onClick={() => {
                      setSelectedType(type)
                      setName(`My ${cfg.name}`)
                      setStep('configure')
                    }}
                    className="p-4 rounded-xl border-2 border-gray-200 hover:border-blue-500 hover:bg-blue-50 transition-all text-left"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-12 h-12 rounded-lg ${cfg.color} flex items-center justify-center text-xl`}
                      >
                        {cfg.icon}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900">{cfg.name}</h3>
                        <p className="text-sm text-gray-500">{cfg.description}</p>
                      </div>
                    </div>
                  </button>
                )
              )}
            </div>
          ) : selectedType ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Integration Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="e.g., Production Jira"
                />
              </div>

              {configFields[selectedType].map((field) => (
                <div key={field.key}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {field.label}
                    {field.required && <span className="text-red-500 ml-1">*</span>}
                  </label>
                  <input
                    type={field.type}
                    value={config[field.key] || ''}
                    onChange={(e) =>
                      setConfig((prev) => ({ ...prev, [field.key]: e.target.value }))
                    }
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={field.label}
                  />
                </div>
              ))}
            </div>
          ) : null}
        </div>

        <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
          {step === 'configure' && (
            <button
              onClick={() => setStep('select')}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Back
            </button>
          )}
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          {step === 'configure' && (
            <button
              onClick={handleSubmit}
              disabled={!name.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              Add Integration
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// Configuration modal
function ConfigureModal({
  integration,
  onClose,
  onSave,
}: {
  integration: Integration
  onClose: () => void
  onSave: (updates: Partial<Integration>) => void
}) {
  const [name, setName] = useState(integration.name)
  const [config, setConfig] = useState<Record<string, string>>(
    integration.config as Record<string, string>
  )

  const configFields: Record<Integration['type'], Array<{ key: string; label: string; type: string }>> = {
    jira: [
      { key: 'base_url', label: 'Jira URL', type: 'url' },
      { key: 'username', label: 'Username/Email', type: 'text' },
      { key: 'api_token', label: 'API Token', type: 'password' },
      { key: 'project_key', label: 'Default Project Key', type: 'text' },
    ],
    servicenow: [
      { key: 'instance_url', label: 'Instance URL', type: 'url' },
      { key: 'username', label: 'Username', type: 'text' },
      { key: 'password', label: 'Password', type: 'password' },
    ],
    github: [
      { key: 'token', label: 'Personal Access Token', type: 'password' },
      { key: 'owner', label: 'Repository Owner', type: 'text' },
      { key: 'repo', label: 'Repository Name', type: 'text' },
    ],
    slack: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'url' },
      { key: 'channel', label: 'Default Channel', type: 'text' },
    ],
    pagerduty: [
      { key: 'api_key', label: 'API Key', type: 'password' },
      { key: 'service_id', label: 'Service ID', type: 'text' },
    ],
    teams: [
      { key: 'webhook_url', label: 'Webhook URL', type: 'url' },
    ],
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl w-full max-w-lg mx-4">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-gray-900">
              Configure {integrationConfig[integration.type]?.name}
            </h2>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <XCircle className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Integration Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>

          {configFields[integration.type]?.map((field) => (
            <div key={field.key}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field.label}
              </label>
              <input
                type={field.type}
                value={config[field.key] || ''}
                onChange={(e) =>
                  setConfig((prev) => ({ ...prev, [field.key]: e.target.value }))
                }
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={field.type === 'password' ? '••••••••' : ''}
              />
            </div>
          ))}
        </div>

        <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onSave({ name, config })}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  )
}

// Demo data
const demoIntegrations: Integration[] = [
  {
    integration_id: 'int_001',
    type: 'jira',
    name: 'Production Jira',
    enabled: true,
    config: { base_url: 'https://company.atlassian.net', project_key: 'OBS' },
    status: 'connected',
    last_sync: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 30).toISOString(),
  },
  {
    integration_id: 'int_002',
    type: 'slack',
    name: 'Engineering Alerts',
    enabled: true,
    config: { webhook_url: 'https://hooks.slack.com/...', channel: '#alerts' },
    status: 'connected',
    last_sync: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 20).toISOString(),
  },
  {
    integration_id: 'int_003',
    type: 'pagerduty',
    name: 'On-Call Alerts',
    enabled: true,
    config: { service_id: 'P123ABC' },
    status: 'error',
    error_message: 'API key expired. Please update credentials.',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 45).toISOString(),
  },
  {
    integration_id: 'int_004',
    type: 'github',
    name: 'Platform Repo',
    enabled: false,
    config: { owner: 'company', repo: 'platform' },
    status: 'disconnected',
    created_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
  },
]

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [configuring, setConfiguring] = useState<Integration | null>(null)
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({})

  useEffect(() => {
    loadIntegrations()
  }, [])

  const loadIntegrations = async () => {
    setIsLoading(true)
    try {
      const data = await api.getIntegrations()
      setIntegrations(data)
    } catch (error) {
      console.log('Using demo integrations data')
      setIntegrations(demoIntegrations)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAdd = async (request: CreateIntegrationRequest) => {
    try {
      const newIntegration = await api.createIntegration(request)
      setIntegrations((prev) => [...prev, newIntegration])
    } catch (error) {
      // Demo: add locally
      const newIntegration: Integration = {
        integration_id: `int_${Date.now()}`,
        ...request,
        enabled: true,
        status: 'connected',
        created_at: new Date().toISOString(),
      }
      setIntegrations((prev) => [...prev, newIntegration])
    }
    setShowAddModal(false)
  }

  const handleTest = async (id: string) => {
    try {
      const result = await api.testIntegration(id)
      setTestResults((prev) => ({ ...prev, [id]: result }))
      // Update status based on test result
      setIntegrations((prev) =>
        prev.map((i) =>
          i.integration_id === id
            ? { ...i, status: result.success ? 'connected' : 'error', error_message: result.success ? undefined : result.message }
            : i
        )
      )
    } catch (error) {
      // Demo: simulate test
      const success = Math.random() > 0.3
      setTestResults((prev) => ({
        ...prev,
        [id]: { success, message: success ? 'Connection successful' : 'Connection failed' },
      }))
    }
  }

  const handleSync = async (id: string) => {
    try {
      await api.syncIntegration(id)
      setIntegrations((prev) =>
        prev.map((i) =>
          i.integration_id === id ? { ...i, last_sync: new Date().toISOString() } : i
        )
      )
    } catch (error) {
      // Demo: update locally
      setIntegrations((prev) =>
        prev.map((i) =>
          i.integration_id === id ? { ...i, last_sync: new Date().toISOString() } : i
        )
      )
    }
  }

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await api.updateIntegration(id, { enabled })
      setIntegrations((prev) =>
        prev.map((i) => (i.integration_id === id ? { ...i, enabled } : i))
      )
    } catch (error) {
      // Demo: update locally
      setIntegrations((prev) =>
        prev.map((i) => (i.integration_id === id ? { ...i, enabled } : i))
      )
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this integration?')) return
    try {
      await api.deleteIntegration(id)
      setIntegrations((prev) => prev.filter((i) => i.integration_id !== id))
    } catch (error) {
      // Demo: delete locally
      setIntegrations((prev) => prev.filter((i) => i.integration_id !== id))
    }
  }

  const handleConfigure = async (id: string, updates: Partial<Integration>) => {
    try {
      const updated = await api.updateIntegration(id, updates)
      setIntegrations((prev) =>
        prev.map((i) => (i.integration_id === id ? updated : i))
      )
    } catch (error) {
      // Demo: update locally
      setIntegrations((prev) =>
        prev.map((i) => (i.integration_id === id ? { ...i, ...updates } : i))
      )
    }
    setConfiguring(null)
  }

  const connectedCount = integrations.filter((i) => i.status === 'connected').length
  const enabledCount = integrations.filter((i) => i.enabled).length

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 bg-blue-100 rounded-xl">
            <Puzzle className="w-8 h-8 text-blue-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Integration Hub</h1>
            <p className="text-gray-500">Connect with your favorite tools and services</p>
          </div>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Integration
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{connectedCount}</p>
              <p className="text-sm text-gray-500">Connected</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Zap className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{enabledCount}</p>
              <p className="text-sm text-gray-500">Active</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Puzzle className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{integrations.length}</p>
              <p className="text-sm text-gray-500">Total</p>
            </div>
          </div>
        </div>
      </div>

      {/* Integrations List */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      ) : integrations.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
          <Puzzle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No integrations yet</h3>
          <p className="text-gray-500 mb-6">
            Connect your first integration to start syncing alerts and incidents
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Integration
          </button>
        </div>
      ) : (
        <div className="grid gap-6">
          {integrations.map((integration) => (
            <IntegrationCard
              key={integration.integration_id}
              integration={integration}
              onTest={() => handleTest(integration.integration_id)}
              onSync={() => handleSync(integration.integration_id)}
              onConfigure={() => setConfiguring(integration)}
              onDelete={() => handleDelete(integration.integration_id)}
              onToggle={() => handleToggle(integration.integration_id, !integration.enabled)}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      {showAddModal && (
        <AddIntegrationModal onClose={() => setShowAddModal(false)} onAdd={handleAdd} />
      )}

      {configuring && (
        <ConfigureModal
          integration={configuring}
          onClose={() => setConfiguring(null)}
          onSave={(updates) => handleConfigure(configuring.integration_id, updates)}
        />
      )}
    </div>
  )
}
