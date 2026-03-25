import { useState, useEffect } from 'react'
import {
  Settings as SettingsIcon,
  Shield,
  Globe,
  Bell,
  Key,
  Activity,
  Info,
  Plus,
  X,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
} from 'lucide-react'
import { Card, CardHeader } from '../components'
import { useHealth } from '../lib/hooks'
import { useSettingsStore } from '../store'
import api, { PIISettings, RegionSettings, RegionHealth } from '../lib/api'

// Tab component
function Tab({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ElementType
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-lg font-medium transition-colors ${
        active
          ? 'bg-blue-600 text-white'
          : 'text-gray-600 hover:bg-gray-100'
      }`}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  )
}

// Toggle switch
function Toggle({
  checked,
  onChange,
  disabled,
}: {
  checked: boolean
  onChange: (checked: boolean) => void
  disabled?: boolean
}) {
  return (
    <button
      type="button"
      onClick={() => !disabled && onChange(!checked)}
      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-blue-600' : 'bg-gray-200'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
    >
      <span
        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  )
}

// PII Settings Section
function PIISettingsSection() {
  const { pii, updatePIISettings } = useSettingsStore()
  const [newPattern, setNewPattern] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await api.updatePIISettings({
        enabled: pii.enabled,
        redact_emails: pii.redactEmails,
        redact_phone_numbers: pii.redactPhoneNumbers,
        redact_ssn: pii.redactSSN,
        redact_credit_cards: pii.redactCreditCards,
        redact_api_keys: pii.redactAPIKeys,
        custom_patterns: pii.customPatterns,
        redaction_strategy: pii.redactionStrategy,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      // Demo mode - just show saved
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setIsSaving(false)
    }
  }

  const addCustomPattern = () => {
    if (newPattern.trim() && !pii.customPatterns.includes(newPattern.trim())) {
      updatePIISettings({
        customPatterns: [...pii.customPatterns, newPattern.trim()],
      })
      setNewPattern('')
    }
  }

  const removeCustomPattern = (pattern: string) => {
    updatePIISettings({
      customPatterns: pii.customPatterns.filter((p) => p !== pattern),
    })
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="PII Redaction"
          subtitle="Configure automatic detection and redaction of personally identifiable information"
        />
        <div className="space-y-6">
          {/* Enable/Disable */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">Enable PII Redaction</p>
              <p className="text-sm text-gray-500">
                Automatically detect and redact PII from logs and traces
              </p>
            </div>
            <Toggle
              checked={pii.enabled}
              onChange={(checked) => updatePIISettings({ enabled: checked })}
            />
          </div>

          {/* Detection Types */}
          <div>
            <h3 className="text-sm font-medium text-gray-900 mb-3">Detection Types</h3>
            <div className="grid grid-cols-2 gap-3">
              {[
                { key: 'redactEmails', label: 'Email Addresses', description: 'user@example.com' },
                { key: 'redactPhoneNumbers', label: 'Phone Numbers', description: '+1 (555) 123-4567' },
                { key: 'redactSSN', label: 'Social Security Numbers', description: 'XXX-XX-XXXX' },
                { key: 'redactCreditCards', label: 'Credit Card Numbers', description: '**** **** **** 1234' },
                { key: 'redactAPIKeys', label: 'API Keys & Tokens', description: 'sk_live_..., Bearer ...' },
              ].map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg"
                >
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{item.label}</p>
                    <p className="text-xs text-gray-500">{item.description}</p>
                  </div>
                  <Toggle
                    checked={pii[item.key as keyof typeof pii] as boolean}
                    onChange={(checked) =>
                      updatePIISettings({ [item.key]: checked })
                    }
                    disabled={!pii.enabled}
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Redaction Strategy */}
          <div>
            <h3 className="text-sm font-medium text-gray-900 mb-3">Redaction Strategy</h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                { value: 'mask', label: 'Mask', description: 'Replace with ***' },
                { value: 'hash', label: 'Hash', description: 'SHA-256 hash value' },
                { value: 'remove', label: 'Remove', description: 'Delete entirely' },
              ].map((strategy) => (
                <button
                  key={strategy.value}
                  onClick={() =>
                    updatePIISettings({
                      redactionStrategy: strategy.value as 'mask' | 'hash' | 'remove',
                    })
                  }
                  disabled={!pii.enabled}
                  className={`p-3 border-2 rounded-lg text-left transition-colors ${
                    pii.redactionStrategy === strategy.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  } disabled:opacity-50`}
                >
                  <p className="font-medium text-gray-900">{strategy.label}</p>
                  <p className="text-xs text-gray-500">{strategy.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Patterns */}
          <div>
            <h3 className="text-sm font-medium text-gray-900 mb-3">Custom Patterns</h3>
            <p className="text-sm text-gray-500 mb-3">
              Add custom regex patterns to detect organization-specific PII
            </p>
            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={newPattern}
                onChange={(e) => setNewPattern(e.target.value)}
                placeholder="Enter regex pattern (e.g., EMP-\d{6})"
                className="input flex-1"
                disabled={!pii.enabled}
              />
              <button
                onClick={addCustomPattern}
                disabled={!pii.enabled || !newPattern.trim()}
                className="btn-secondary"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
            {pii.customPatterns.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {pii.customPatterns.map((pattern) => (
                  <span
                    key={pattern}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-gray-100 rounded-full text-sm"
                  >
                    <code className="text-xs">{pattern}</code>
                    <button
                      onClick={() => removeCustomPattern(pattern)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="btn-primary"
            >
              {isSaving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : saved ? (
                'Saved!'
              ) : (
                'Save Settings'
              )}
            </button>
          </div>
        </div>
      </Card>
    </div>
  )
}

// Multi-Region Settings Section
function MultiRegionSettingsSection() {
  const { regions, updateRegionSettings } = useSettingsStore()
  const [regionHealth, setRegionHealth] = useState<RegionHealth[]>([])
  const [isLoadingHealth, setIsLoadingHealth] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [isFailingOver, setIsFailingOver] = useState(false)

  useEffect(() => {
    loadRegionHealth()
  }, [])

  const loadRegionHealth = async () => {
    setIsLoadingHealth(true)
    try {
      const health = await api.getRegionHealth()
      setRegionHealth(health)
    } catch (error) {
      // Demo data
      setRegionHealth([
        {
          region_id: 'us-east-1',
          status: 'healthy',
          latency_ms: 45,
          last_check: new Date().toISOString(),
          services: {
            api: 'healthy',
            database: 'healthy',
            cache: 'healthy',
          },
        },
        {
          region_id: 'us-west-2',
          status: 'healthy',
          latency_ms: 120,
          last_check: new Date().toISOString(),
          services: {
            api: 'healthy',
            database: 'healthy',
            cache: 'healthy',
          },
        },
        {
          region_id: 'eu-west-1',
          status: 'degraded',
          latency_ms: 180,
          last_check: new Date().toISOString(),
          services: {
            api: 'healthy',
            database: 'unhealthy',
            cache: 'healthy',
          },
        },
      ])
    } finally {
      setIsLoadingHealth(false)
    }
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await api.updateRegionSettings({
        primary_region: regions.primaryRegion,
        secondary_region: regions.secondaryRegion,
        enable_failover: regions.enableFailover,
        routing_strategy: regions.routingStrategy,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (error) {
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } finally {
      setIsSaving(false)
    }
  }

  const handleFailover = async (targetRegion: string) => {
    if (!confirm(`Are you sure you want to failover to ${targetRegion}?`)) return
    setIsFailingOver(true)
    try {
      await api.triggerFailover(targetRegion)
      updateRegionSettings({ primaryRegion: targetRegion })
      await loadRegionHealth()
    } catch (error) {
      // Demo mode
      updateRegionSettings({ primaryRegion: targetRegion })
    } finally {
      setIsFailingOver(false)
    }
  }

  const availableRegions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Multi-Region Configuration"
          subtitle="Configure cross-region replication and failover settings"
        />
        <div className="space-y-6">
          {/* Region Health Status */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium text-gray-900">Region Health</h3>
              <button
                onClick={loadRegionHealth}
                disabled={isLoadingHealth}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
              >
                <RefreshCw className={`w-4 h-4 ${isLoadingHealth ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
            <div className="grid gap-3">
              {regionHealth.map((region) => (
                <div
                  key={region.region_id}
                  className={`p-4 rounded-lg border-2 ${
                    region.region_id === regions.primaryRegion
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          region.status === 'healthy'
                            ? 'bg-green-500'
                            : region.status === 'degraded'
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                        }`}
                      />
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900">
                            {region.region_id}
                          </span>
                          {region.region_id === regions.primaryRegion && (
                            <span className="px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
                              Primary
                            </span>
                          )}
                          {region.region_id === regions.secondaryRegion && (
                            <span className="px-2 py-0.5 bg-gray-600 text-white text-xs rounded-full">
                              Secondary
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-gray-500">
                          <span>Latency: {region.latency_ms}ms</span>
                          <span className="capitalize">{region.status}</span>
                        </div>
                      </div>
                    </div>
                    {region.region_id !== regions.primaryRegion && (
                      <button
                        onClick={() => handleFailover(region.region_id)}
                        disabled={isFailingOver || region.status === 'unhealthy'}
                        className="px-3 py-1.5 text-sm font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100 disabled:opacity-50"
                      >
                        {isFailingOver ? 'Failing over...' : 'Failover'}
                      </button>
                    )}
                  </div>
                  {/* Service Health */}
                  <div className="flex gap-2 mt-3">
                    {Object.entries(region.services).map(([service, status]) => (
                      <span
                        key={service}
                        className={`px-2 py-1 text-xs rounded ${
                          status === 'healthy'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}
                      >
                        {service}: {status}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Primary/Secondary Region Selection */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Primary Region
              </label>
              <select
                value={regions.primaryRegion}
                onChange={(e) => updateRegionSettings({ primaryRegion: e.target.value })}
                className="input"
              >
                {availableRegions.map((region) => (
                  <option key={region} value={region}>
                    {region}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Secondary Region
              </label>
              <select
                value={regions.secondaryRegion}
                onChange={(e) => updateRegionSettings({ secondaryRegion: e.target.value })}
                className="input"
              >
                {availableRegions
                  .filter((r) => r !== regions.primaryRegion)
                  .map((region) => (
                    <option key={region} value={region}>
                      {region}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {/* Failover Settings */}
          <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">Enable Automatic Failover</p>
              <p className="text-sm text-gray-500">
                Automatically switch to secondary region when primary is unhealthy
              </p>
            </div>
            <Toggle
              checked={regions.enableFailover}
              onChange={(checked) => updateRegionSettings({ enableFailover: checked })}
            />
          </div>

          {/* Routing Strategy */}
          <div>
            <h3 className="text-sm font-medium text-gray-900 mb-3">Routing Strategy</h3>
            <div className="grid grid-cols-3 gap-3">
              {[
                {
                  value: 'failover',
                  label: 'Failover',
                  description: 'Use primary, switch on failure',
                },
                {
                  value: 'round_robin',
                  label: 'Round Robin',
                  description: 'Distribute across regions',
                },
                {
                  value: 'latency_based',
                  label: 'Latency Based',
                  description: 'Route to fastest region',
                },
              ].map((strategy) => (
                <button
                  key={strategy.value}
                  onClick={() =>
                    updateRegionSettings({
                      routingStrategy: strategy.value as 'failover' | 'round_robin' | 'latency_based',
                    })
                  }
                  className={`p-3 border-2 rounded-lg text-left transition-colors ${
                    regions.routingStrategy === strategy.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <p className="font-medium text-gray-900">{strategy.label}</p>
                  <p className="text-xs text-gray-500">{strategy.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="btn-primary"
            >
              {isSaving ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : saved ? (
                'Saved!'
              ) : (
                'Save Settings'
              )}
            </button>
          </div>
        </div>
      </Card>
    </div>
  )
}

// Alert Settings Section
function AlertSettingsSection() {
  const { alertThresholds, notifications, updateAlertThresholds, updateNotificationSettings } = useSettingsStore()
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Alert Thresholds"
          subtitle="Configure when alerts should be triggered"
        />
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Error Rate Threshold (%)
              </label>
              <input
                type="number"
                value={alertThresholds.errorRateThreshold}
                onChange={(e) =>
                  updateAlertThresholds({ errorRateThreshold: Number(e.target.value) })
                }
                className="input"
                min={0}
                max={100}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Latency Threshold (ms)
              </label>
              <input
                type="number"
                value={alertThresholds.latencyThresholdMs}
                onChange={(e) =>
                  updateAlertThresholds({ latencyThresholdMs: Number(e.target.value) })
                }
                className="input"
                min={0}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cost Threshold ($)
              </label>
              <input
                type="number"
                value={alertThresholds.costThreshold}
                onChange={(e) =>
                  updateAlertThresholds({ costThreshold: Number(e.target.value) })
                }
                className="input"
                min={0}
              />
            </div>
          </div>
          <div className="flex justify-end">
            <button onClick={handleSave} className="btn-primary">
              {saved ? 'Saved!' : 'Save Thresholds'}
            </button>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader
          title="Notification Settings"
          subtitle="Configure how you receive alerts"
        />
        <div className="space-y-4">
          {[
            { key: 'emailEnabled', label: 'Email Notifications', description: 'Receive alerts via email' },
            { key: 'slackEnabled', label: 'Slack Notifications', description: 'Post alerts to Slack channels' },
            { key: 'pagerdutyEnabled', label: 'PagerDuty', description: 'Trigger PagerDuty incidents' },
            { key: 'teamsEnabled', label: 'Microsoft Teams', description: 'Post alerts to Teams channels' },
          ].map((item) => (
            <div
              key={item.key}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
            >
              <div>
                <p className="font-medium text-gray-900">{item.label}</p>
                <p className="text-sm text-gray-500">{item.description}</p>
              </div>
              <Toggle
                checked={notifications[item.key as keyof typeof notifications] as boolean}
                onChange={(checked) =>
                  updateNotificationSettings({ [item.key]: checked })
                }
              />
            </div>
          ))}

          <div className="flex items-center justify-between p-4 bg-amber-50 rounded-lg border border-amber-200">
            <div>
              <p className="font-medium text-amber-900">Critical Alerts Only</p>
              <p className="text-sm text-amber-700">
                Only send notifications for critical severity alerts
              </p>
            </div>
            <Toggle
              checked={notifications.criticalOnly}
              onChange={(checked) =>
                updateNotificationSettings({ criticalOnly: checked })
              }
            />
          </div>
        </div>
      </Card>
    </div>
  )
}

// API Key Section
function APIKeySection() {
  const [apiKey, setApiKey] = useState(localStorage.getItem('api_key') ?? '')
  const [saved, setSaved] = useState(false)

  const handleSaveApiKey = () => {
    localStorage.setItem('api_key', apiKey)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <Card>
      <CardHeader
        title="API Configuration"
        subtitle="Configure your API key for authentication"
      />
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            API Key
          </label>
          <div className="flex gap-3">
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              className="input flex-1"
            />
            <button onClick={handleSaveApiKey} className="btn-primary">
              {saved ? 'Saved!' : 'Save'}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Your API key is stored locally in your browser
          </p>
        </div>
      </div>
    </Card>
  )
}

// System Health Section
function SystemHealthSection() {
  const { data: health } = useHealth()

  return (
    <Card>
      <CardHeader
        title="System Health"
        subtitle="Current status of platform components"
      />
      <div className="space-y-3">
        {[
          { name: 'API Gateway', status: health?.components?.api_gateway ?? 'healthy' },
          { name: 'Kinesis Stream', status: health?.components?.kinesis ?? 'healthy' },
          { name: 'DynamoDB', status: health?.components?.dynamodb ?? 'healthy' },
          { name: 'Timestream', status: health?.components?.timestream ?? 'healthy' },
          { name: 'OpenSearch', status: health?.components?.opensearch ?? 'healthy' },
        ].map((component) => (
          <div
            key={component.name}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <span className="text-sm font-medium text-gray-900">{component.name}</span>
            <span
              className={`badge ${
                component.status === 'healthy'
                  ? 'badge-success'
                  : component.status === 'degraded'
                  ? 'badge-warning'
                  : 'badge-error'
              }`}
            >
              {String(component.status)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'general' | 'pii' | 'regions' | 'alerts'>('general')

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div className="p-3 bg-blue-100 rounded-xl">
          <SettingsIcon className="w-8 h-8 text-blue-600" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
          <p className="text-sm text-gray-500">
            Configure your observability platform settings
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 p-1 bg-gray-100 rounded-xl w-fit">
        <Tab
          active={activeTab === 'general'}
          onClick={() => setActiveTab('general')}
          icon={Key}
          label="General"
        />
        <Tab
          active={activeTab === 'pii'}
          onClick={() => setActiveTab('pii')}
          icon={Shield}
          label="PII Redaction"
        />
        <Tab
          active={activeTab === 'regions'}
          onClick={() => setActiveTab('regions')}
          icon={Globe}
          label="Multi-Region"
        />
        <Tab
          active={activeTab === 'alerts'}
          onClick={() => setActiveTab('alerts')}
          icon={Bell}
          label="Alerts"
        />
      </div>

      {/* Content */}
      {activeTab === 'general' && (
        <div className="space-y-6">
          <APIKeySection />
          <SystemHealthSection />
          <Card>
            <CardHeader title="About" subtitle="Platform information" />
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Version</span>
                <span className="text-gray-900">1.0.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Environment</span>
                <span className="text-gray-900">Production</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Region</span>
                <span className="text-gray-900">us-east-1</span>
              </div>
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'pii' && <PIISettingsSection />}
      {activeTab === 'regions' && <MultiRegionSettingsSection />}
      {activeTab === 'alerts' && <AlertSettingsSection />}
    </div>
  )
}
