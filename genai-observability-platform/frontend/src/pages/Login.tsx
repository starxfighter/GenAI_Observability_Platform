import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Eye, EyeOff, Shield, Loader2, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuthStore } from '../store'
import api, { AuthProvider } from '../lib/api'

// SSO Provider icons
const providerIcons: Record<string, { icon: string; color: string }> = {
  google: { icon: '🔵', color: 'hover:bg-blue-50 border-blue-200' },
  okta: { icon: '🟦', color: 'hover:bg-indigo-50 border-indigo-200' },
  auth0: { icon: '🔴', color: 'hover:bg-red-50 border-red-200' },
  azure: { icon: '🔷', color: 'hover:bg-cyan-50 border-cyan-200' },
  default: { icon: '🔐', color: 'hover:bg-gray-50 border-gray-200' },
}

// Demo providers
const demoProviders: AuthProvider[] = [
  { id: 'google', name: 'Google Workspace', type: 'oidc' },
  { id: 'okta', name: 'Okta', type: 'oidc' },
  { id: 'azure', name: 'Azure AD', type: 'saml' },
]

export default function LoginPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, isAuthenticated } = useAuthStore()

  const [providers, setProviders] = useState<AuthProvider[]>([])
  const [isLoadingProviders, setIsLoadingProviders] = useState(true)
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [isLoggingIn, setIsLoggingIn] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // API Key login state
  const [showApiKeyLogin, setShowApiKeyLogin] = useState(false)
  const [apiKey, setApiKey] = useState('')
  const [showApiKey, setShowApiKey] = useState(false)

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/')
    }
  }, [isAuthenticated, navigate])

  // Handle OAuth callback
  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setError(`Authentication failed: ${searchParams.get('error_description') || errorParam}`)
      return
    }

    if (code && state) {
      handleOAuthCallback(code, state)
    }
  }, [searchParams])

  // Load SSO providers
  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    setIsLoadingProviders(true)
    try {
      const data = await api.getAuthProviders()
      setProviders(data)
    } catch (error) {
      console.log('Using demo providers')
      setProviders(demoProviders)
    } finally {
      setIsLoadingProviders(false)
    }
  }

  const handleOAuthCallback = async (code: string, state: string) => {
    setIsLoggingIn(true)
    setError(null)

    try {
      // Get provider from state
      const provider = sessionStorage.getItem('oauth_provider') || 'google'
      const response = await api.handleAuthCallback(provider, { code, state })

      // Store tokens and user info
      localStorage.setItem('api_key', response.access_token)
      login(response.user, response.access_token)

      setSuccess('Successfully logged in!')
      setTimeout(() => navigate('/'), 1000)
    } catch (error: any) {
      setError(error.message || 'Failed to complete authentication')
    } finally {
      setIsLoggingIn(false)
    }
  }

  const handleSSOLogin = async (providerId: string) => {
    setSelectedProvider(providerId)
    setError(null)

    try {
      const redirectUri = `${window.location.origin}/login`
      const { login_url, state } = await api.getLoginUrl(providerId, redirectUri)

      // Store state for callback
      sessionStorage.setItem('oauth_state', state)
      sessionStorage.setItem('oauth_provider', providerId)

      // Redirect to SSO provider
      window.location.href = login_url
    } catch (error) {
      // Demo mode: simulate successful login
      console.log('Demo SSO login for:', providerId)
      setIsLoggingIn(true)

      setTimeout(() => {
        const demoUser = {
          user_id: 'user_demo',
          email: 'demo@example.com',
          name: 'Demo User',
          picture: undefined,
          provider: providerId,
          roles: ['admin'],
          groups: ['engineering'],
        }
        const demoToken = 'demo_token_' + Date.now()

        localStorage.setItem('api_key', demoToken)
        login(demoUser, demoToken)

        setSuccess('Successfully logged in!')
        setTimeout(() => navigate('/'), 1000)
      }, 1500)
    }
  }

  const handleApiKeyLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!apiKey.trim()) return

    setIsLoggingIn(true)
    setError(null)

    try {
      // Store API key and verify it
      localStorage.setItem('api_key', apiKey)
      const user = await api.getCurrentUser()

      login(user, apiKey)
      setSuccess('Successfully logged in!')
      setTimeout(() => navigate('/'), 1000)
    } catch (error) {
      // Demo mode
      if (apiKey.startsWith('demo') || apiKey.length > 10) {
        const demoUser = {
          user_id: 'user_api',
          email: 'api-user@example.com',
          name: 'API User',
          provider: 'api_key',
          roles: ['user'],
          groups: [],
        }
        login(demoUser, apiKey)
        setSuccess('Successfully logged in!')
        setTimeout(() => navigate('/'), 1000)
      } else {
        localStorage.removeItem('api_key')
        setError('Invalid API key')
      }
    } finally {
      setIsLoggingIn(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600 rounded-2xl mb-4">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">GenAI Observability</h1>
          <p className="text-gray-500 mt-1">Sign in to continue to your dashboard</p>
        </div>

        {/* Login Card */}
        <div className="bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
          {/* Status Messages */}
          {error && (
            <div className="p-4 bg-red-50 border-b border-red-100 flex items-center gap-3">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
          {success && (
            <div className="p-4 bg-green-50 border-b border-green-100 flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0" />
              <p className="text-sm text-green-700">{success}</p>
            </div>
          )}

          <div className="p-6">
            {!showApiKeyLogin ? (
              <>
                {/* SSO Providers */}
                <div className="space-y-3">
                  <p className="text-sm font-medium text-gray-700 mb-4">
                    Sign in with your organization
                  </p>

                  {isLoadingProviders ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                    </div>
                  ) : (
                    providers.map((provider) => {
                      const icon = providerIcons[provider.id] || providerIcons.default
                      return (
                        <button
                          key={provider.id}
                          onClick={() => handleSSOLogin(provider.id)}
                          disabled={isLoggingIn}
                          className={`w-full flex items-center justify-between px-4 py-3 border-2 rounded-xl transition-all ${icon.color} disabled:opacity-50`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="text-xl">{icon.icon}</span>
                            <span className="font-medium text-gray-900">{provider.name}</span>
                          </div>
                          {selectedProvider === provider.id && isLoggingIn ? (
                            <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
                          ) : (
                            <span className="text-xs text-gray-400 uppercase">{provider.type}</span>
                          )}
                        </button>
                      )
                    })
                  )}
                </div>

                {/* Divider */}
                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-gray-200" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-3 bg-white text-gray-500">or</span>
                  </div>
                </div>

                {/* API Key Login Link */}
                <button
                  onClick={() => setShowApiKeyLogin(true)}
                  className="w-full text-center text-sm text-blue-600 hover:text-blue-700 font-medium"
                >
                  Sign in with API Key
                </button>
              </>
            ) : (
              <>
                {/* API Key Form */}
                <form onSubmit={handleApiKeyLogin} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      API Key
                    </label>
                    <div className="relative">
                      <input
                        type={showApiKey ? 'text' : 'password'}
                        value={apiKey}
                        onChange={(e) => setApiKey(e.target.value)}
                        className="w-full px-4 py-2.5 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 pr-10"
                        placeholder="Enter your API key"
                        disabled={isLoggingIn}
                      />
                      <button
                        type="button"
                        onClick={() => setShowApiKey(!showApiKey)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showApiKey ? (
                          <EyeOff className="w-5 h-5" />
                        ) : (
                          <Eye className="w-5 h-5" />
                        )}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">
                      You can find your API key in your profile settings
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoggingIn || !apiKey.trim()}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {isLoggingIn ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      'Sign In'
                    )}
                  </button>
                </form>

                {/* Back to SSO */}
                <button
                  onClick={() => {
                    setShowApiKeyLogin(false)
                    setError(null)
                  }}
                  className="w-full text-center text-sm text-gray-500 hover:text-gray-700 mt-4"
                >
                  Back to SSO login
                </button>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
            <p className="text-xs text-gray-500 text-center">
              By signing in, you agree to our{' '}
              <a href="#" className="text-blue-600 hover:underline">
                Terms of Service
              </a>{' '}
              and{' '}
              <a href="#" className="text-blue-600 hover:underline">
                Privacy Policy
              </a>
            </p>
          </div>
        </div>

        {/* Help */}
        <p className="text-center text-sm text-gray-500 mt-6">
          Need help?{' '}
          <a href="#" className="text-blue-600 hover:underline">
            Contact support
          </a>
        </p>
      </div>
    </div>
  )
}
