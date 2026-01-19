import { defineStore } from 'pinia'
import axios from 'axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: null,
    user: null,
    isAuthenticated: false,
    isLoading: true,
    authError: null,
    // Runtime mode detection (from backend)
    emailAuthEnabled: null,  // Email-based authentication
    modeDetected: false,
    // RBAC: Role and permissions (E17-07)
    role: null,                // e.g., 'process_operator'
    roleDisplay: null,         // e.g., 'Process Operator'
    permissions: [],           // e.g., ['process:read', 'execution:trigger']
    permissionsLoaded: false
  }),

  getters: {
    authHeader() {
      return this.token ? { Authorization: `Bearer ${this.token}` } : {}
    },

    userEmail() {
      return this.user?.email || null
    },

    userName() {
      return this.user?.name || this.user?.email || 'User'
    },

    userInitials() {
      const name = this.userName
      if (!name) return '?'
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    },

    userPicture() {
      return this.user?.picture || null
    },

    // RBAC Getters (E17-07)
    isAdmin() {
      return this.role === 'process_admin'
    },

    isDesigner() {
      return this.role === 'process_designer' || this.isAdmin
    },

    isOperator() {
      return this.role === 'process_operator' || this.isAdmin
    },

    canCreateProcess() {
      return this.permissions.includes('process:create')
    },

    canUpdateProcess() {
      return this.permissions.includes('process:update')
    },

    canDeleteProcess() {
      return this.permissions.includes('process:delete')
    },

    canPublishProcess() {
      return this.permissions.includes('process:publish')
    },

    canTriggerExecution() {
      return this.permissions.includes('execution:trigger')
    },

    canCancelExecution() {
      return this.permissions.includes('execution:cancel')
    },

    canRetryExecution() {
      return this.permissions.includes('execution:retry')
    },

    canDecideApproval() {
      return this.permissions.includes('approval:decide')
    }
  },

  actions: {
    // Detect authentication mode from backend (called before login)
    async detectAuthMode() {
      try {
        const response = await axios.get('/api/auth/mode')
        this.emailAuthEnabled = response.data.email_auth_enabled !== false
        this.modeDetected = true

        console.log(`🔐 Auth mode: EMAIL=${this.emailAuthEnabled}`)
        return true
      } catch (error) {
        console.error('Failed to detect auth mode:', error)
        // Default to email auth if detection fails
        this.emailAuthEnabled = true
        this.modeDetected = true
        return true
      }
    },

    // Initialize auth - called on app startup
    async initializeAuth() {
      this.isLoading = true
      this.authError = null

      // First detect auth mode from backend
      await this.detectAuthMode()

      const storedToken = localStorage.getItem('token')
      const storedUser = localStorage.getItem('auth0_user')

      if (storedToken && storedUser) {
        try {
          const user = JSON.parse(storedUser)

          // Check token validity
          // Parse JWT to get mode claim (without verification - just for client-side check)
          const tokenPayload = this.parseJwtPayload(storedToken)
          const tokenMode = tokenPayload?.mode

          // Valid token modes: admin, email, prod (Auth0)
          // All modes are accepted - no cross-mode restrictions needed
          if (tokenMode) {
            // Restore the session from localStorage
            this.token = storedToken
            this.user = user
            this.isAuthenticated = true
            this.setupAxiosAuth()
            console.log('✅ Session restored for:', user.email || user.name)

            // Fetch permissions on session restore (E17-07)
            await this.fetchPermissions()
          }
        } catch (e) {
          console.warn('Failed to parse stored user, clearing credentials')
          localStorage.removeItem('token')
          localStorage.removeItem('auth0_user')
        }
      }

      this.isLoading = false
    },

    // Parse JWT payload without verification (client-side mode check only)
    parseJwtPayload(token) {
      try {
        const base64Url = token.split('.')[1]
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
        const jsonPayload = decodeURIComponent(
          atob(base64).split('').map(c =>
            '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
          ).join('')
        )
        return JSON.parse(jsonPayload)
      } catch (e) {
        return null
      }
    },

    // Setup axios authorization header and cookie for nginx
    setupAxiosAuth() {
      if (this.token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${this.token}`
        // Set token as cookie for nginx auth_request to validate agent UI access
        document.cookie = `token=${this.token}; path=/; max-age=1800; SameSite=Strict`
      }
    },

    // Login with username/password (for admin login)
    async loginWithCredentials(username, password) {
      try {
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)

        const response = await axios.post('/api/token', formData)
        this.token = response.data.access_token

        // Create a dev user profile
        const devUser = {
          sub: `local|${username}`,
          email: `${username}@localhost`,
          name: username,
          picture: 'https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y',
          email_verified: true
        }

        this.user = devUser
        this.isAuthenticated = true

        localStorage.setItem('token', this.token)
        localStorage.setItem('auth0_user', JSON.stringify(devUser))
        this.setupAxiosAuth()

        // Fetch permissions after successful login (E17-07)
        await this.fetchPermissions()

        console.log('🔐 Admin login: authenticated as', username)
        return true
      } catch (error) {
        console.error('Admin login failed:', error)
        const detail = error.response?.data?.detail || 'Invalid username or password'
        this.authError = detail
        return false
      }
    },

    // =========================================================================
    // Email-Based Authentication (Phase 12.4)
    // =========================================================================

    // Request a verification code via email
    async requestEmailCode(email) {
      if (!this.emailAuthEnabled) {
        this.authError = 'Email authentication is disabled'
        return { success: false, error: 'Email authentication is disabled' }
      }

      try {
        const response = await axios.post('/api/auth/email/request', { email })
        return {
          success: true,
          message: response.data.message,
          expiresInSeconds: response.data.expires_in_seconds
        }
      } catch (error) {
        console.error('Request email code failed:', error)
        const detail = error.response?.data?.detail || 'Failed to send verification code'
        this.authError = detail
        return { success: false, error: detail }
      }
    },

    // Verify email code and login
    async verifyEmailCode(email, code) {
      if (!this.emailAuthEnabled) {
        this.authError = 'Email authentication is disabled'
        return false
      }

      try {
        const response = await axios.post('/api/auth/email/verify', { email, code })

        this.token = response.data.access_token
        this.user = response.data.user
        this.isAuthenticated = true

        localStorage.setItem('token', this.token)
        localStorage.setItem('auth0_user', JSON.stringify(this.user))
        this.setupAxiosAuth()

        // Fetch permissions after successful login (E17-07)
        await this.fetchPermissions()

        console.log('📧 Email auth: authenticated as', this.user.email)
        return true
      } catch (error) {
        console.error('Verify email code failed:', error)
        const detail = error.response?.data?.detail || 'Invalid or expired verification code'
        this.authError = detail
        return false
      }
    },

    // Logout
    logout() {
      this.token = null
      this.user = null
      this.isAuthenticated = false
      this.authError = null
      // Clear RBAC state
      this.role = null
      this.roleDisplay = null
      this.permissions = []
      this.permissionsLoaded = false

      localStorage.removeItem('token')
      localStorage.removeItem('auth0_user')
      delete axios.defaults.headers.common['Authorization']

      // Clear the token cookie
      document.cookie = 'token=; path=/; max-age=0'
    },

    // Clear auth error
    clearError() {
      this.authError = null
    },

    // =========================================================================
    // RBAC: Fetch user permissions (E17-07)
    // =========================================================================

    /**
     * Fetch the current user's role and permissions from the backend.
     * Called automatically after successful authentication.
     */
    async fetchPermissions() {
      if (!this.isAuthenticated || !this.token) {
        console.warn('Cannot fetch permissions: not authenticated')
        return false
      }

      try {
        const response = await axios.get('/api/users/me/permissions', {
          headers: this.authHeader
        })

        this.role = response.data.role
        this.roleDisplay = response.data.role_display
        this.permissions = response.data.permissions || []
        this.permissionsLoaded = true

        console.log(`🔒 RBAC: Role=${this.roleDisplay}, Permissions=${this.permissions.length}`)
        return true
      } catch (error) {
        console.error('Failed to fetch permissions:', error)
        // Default to viewer permissions on error
        this.role = 'process_viewer'
        this.roleDisplay = 'Viewer'
        this.permissions = ['process:read', 'execution:view']
        this.permissionsLoaded = true
        return false
      }
    },

    /**
     * Check if the current user has a specific permission.
     * @param {string} permission - Permission to check (e.g., 'process:create')
     * @returns {boolean}
     */
    hasPermission(permission) {
      return this.permissions.includes(permission)
    },

    /**
     * Check if the current user has any of the specified permissions.
     * @param {string[]} permissions - Permissions to check
     * @returns {boolean}
     */
    hasAnyPermission(permissions) {
      return permissions.some(p => this.permissions.includes(p))
    },

    /**
     * Check if the current user has all of the specified permissions.
     * @param {string[]} permissions - Permissions to check
     * @returns {boolean}
     */
    hasAllPermissions(permissions) {
      return permissions.every(p => this.permissions.includes(p))
    }
  }
})
