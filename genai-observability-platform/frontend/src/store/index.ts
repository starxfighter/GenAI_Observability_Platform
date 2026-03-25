import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// User and Authentication Store
interface User {
  user_id: string
  email: string
  name: string
  picture?: string
  provider: string
  roles: string[]
  groups: string[]
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (user: User, token: string) => void
  logout: () => void
  updateUser: (updates: Partial<User>) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (user, token) => set({ user, token, isAuthenticated: true }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),
    }),
    {
      name: 'auth-storage',
    }
  )
)

// Settings Store
interface PIISettings {
  enabled: boolean
  redactEmails: boolean
  redactPhoneNumbers: boolean
  redactSSN: boolean
  redactCreditCards: boolean
  redactAPIKeys: boolean
  customPatterns: string[]
  redactionStrategy: 'mask' | 'hash' | 'remove'
}

interface RegionSettings {
  primaryRegion: string
  secondaryRegion: string
  enableFailover: boolean
  routingStrategy: 'failover' | 'round_robin' | 'latency_based'
}

interface IntegrationConfig {
  id: string
  type: 'jira' | 'servicenow' | 'github' | 'slack' | 'pagerduty' | 'teams'
  name: string
  enabled: boolean
  config: Record<string, unknown>
  lastSync?: string
  status: 'connected' | 'disconnected' | 'error'
}

interface NotificationSettings {
  emailEnabled: boolean
  slackEnabled: boolean
  pagerdutyEnabled: boolean
  teamsEnabled: boolean
  criticalOnly: boolean
}

interface SettingsState {
  pii: PIISettings
  regions: RegionSettings
  integrations: IntegrationConfig[]
  notifications: NotificationSettings
  alertThresholds: {
    errorRateThreshold: number
    latencyThresholdMs: number
    costThreshold: number
  }
  updatePIISettings: (settings: Partial<PIISettings>) => void
  updateRegionSettings: (settings: Partial<RegionSettings>) => void
  addIntegration: (integration: IntegrationConfig) => void
  updateIntegration: (id: string, updates: Partial<IntegrationConfig>) => void
  removeIntegration: (id: string) => void
  updateNotificationSettings: (settings: Partial<NotificationSettings>) => void
  updateAlertThresholds: (thresholds: Partial<SettingsState['alertThresholds']>) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      pii: {
        enabled: true,
        redactEmails: true,
        redactPhoneNumbers: true,
        redactSSN: true,
        redactCreditCards: true,
        redactAPIKeys: true,
        customPatterns: [],
        redactionStrategy: 'mask',
      },
      regions: {
        primaryRegion: 'us-east-1',
        secondaryRegion: 'us-west-2',
        enableFailover: true,
        routingStrategy: 'failover',
      },
      integrations: [],
      notifications: {
        emailEnabled: false,
        slackEnabled: false,
        pagerdutyEnabled: false,
        teamsEnabled: false,
        criticalOnly: false,
      },
      alertThresholds: {
        errorRateThreshold: 5,
        latencyThresholdMs: 5000,
        costThreshold: 100,
      },
      updatePIISettings: (settings) =>
        set((state) => ({ pii: { ...state.pii, ...settings } })),
      updateRegionSettings: (settings) =>
        set((state) => ({ regions: { ...state.regions, ...settings } })),
      addIntegration: (integration) =>
        set((state) => ({ integrations: [...state.integrations, integration] })),
      updateIntegration: (id, updates) =>
        set((state) => ({
          integrations: state.integrations.map((i) =>
            i.id === id ? { ...i, ...updates } : i
          ),
        })),
      removeIntegration: (id) =>
        set((state) => ({
          integrations: state.integrations.filter((i) => i.id !== id),
        })),
      updateNotificationSettings: (settings) =>
        set((state) => ({ notifications: { ...state.notifications, ...settings } })),
      updateAlertThresholds: (thresholds) =>
        set((state) => ({
          alertThresholds: { ...state.alertThresholds, ...thresholds },
        })),
    }),
    {
      name: 'settings-storage',
    }
  )
)

// NL Query Store
interface QueryHistoryItem {
  id: string
  query: string
  timestamp: string
  resultCount: number
}

interface SavedQuery {
  id: string
  name: string
  query: string
  description?: string
  createdAt: string
  tags: string[]
}

interface NLQueryState {
  history: QueryHistoryItem[]
  savedQueries: SavedQuery[]
  currentQuery: string
  isLoading: boolean
  addToHistory: (item: QueryHistoryItem) => void
  clearHistory: () => void
  saveQuery: (query: SavedQuery) => void
  deleteQuery: (id: string) => void
  setCurrentQuery: (query: string) => void
  setLoading: (loading: boolean) => void
}

export const useNLQueryStore = create<NLQueryState>()(
  persist(
    (set) => ({
      history: [],
      savedQueries: [],
      currentQuery: '',
      isLoading: false,
      addToHistory: (item) =>
        set((state) => ({
          history: [item, ...state.history].slice(0, 50),
        })),
      clearHistory: () => set({ history: [] }),
      saveQuery: (query) =>
        set((state) => ({ savedQueries: [...state.savedQueries, query] })),
      deleteQuery: (id) =>
        set((state) => ({
          savedQueries: state.savedQueries.filter((q) => q.id !== id),
        })),
      setCurrentQuery: (query) => set({ currentQuery: query }),
      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'nl-query-storage',
    }
  )
)

// Remediation Store
interface RemediationAction {
  id: string
  investigationId: string
  agentId: string
  status: 'pending_approval' | 'approved' | 'rejected' | 'in_progress' | 'completed' | 'failed' | 'rolled_back'
  actionPlan: {
    actions: Array<{
      step: number
      type: string
      description: string
      automated: boolean
      riskLevel: 'low' | 'medium' | 'high'
    }>
    estimatedDuration: number
    riskAssessment: string
  }
  createdAt: string
  executedAt?: string
  completedAt?: string
  rollbackAvailable: boolean
}

interface RemediationState {
  remediations: RemediationAction[]
  selectedRemediation: RemediationAction | null
  addRemediation: (remediation: RemediationAction) => void
  updateRemediation: (id: string, updates: Partial<RemediationAction>) => void
  selectRemediation: (remediation: RemediationAction | null) => void
}

export const useRemediationStore = create<RemediationState>((set) => ({
  remediations: [],
  selectedRemediation: null,
  addRemediation: (remediation) =>
    set((state) => ({ remediations: [remediation, ...state.remediations] })),
  updateRemediation: (id, updates) =>
    set((state) => ({
      remediations: state.remediations.map((r) =>
        r.id === id ? { ...r, ...updates } : r
      ),
    })),
  selectRemediation: (remediation) => set({ selectedRemediation: remediation }),
}))

// UI Store
interface UIState {
  sidebarOpen: boolean
  theme: 'light' | 'dark' | 'system'
  timeRange: '1h' | '6h' | '24h' | '7d' | '30d'
  setSidebarOpen: (open: boolean) => void
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  setTimeRange: (range: '1h' | '6h' | '24h' | '7d' | '30d') => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'light',
      timeRange: '24h',
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setTheme: (theme) => set({ theme }),
      setTimeRange: (range) => set({ timeRange: range }),
    }),
    {
      name: 'ui-storage',
    }
  )
)
