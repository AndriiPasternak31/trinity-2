/**
 * usePermissions Composable
 *
 * Provides convenient access to RBAC permissions in Vue components.
 * Wraps the auth store's permission getters with additional helpers.
 *
 * Reference: BACKLOG_ACCESS_AUDIT.md - E17-07
 *
 * @example
 * const { can, isAdmin, canCreateProcess } = usePermissions()
 *
 * if (can('process:create')) {
 *   // Show create button
 * }
 */

import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermissions() {
  const authStore = useAuthStore()

  // =========================================================================
  // Core Permission Checks
  // =========================================================================

  /**
   * Check if the current user has a specific permission.
   * @param {string} permission - Permission string (e.g., 'process:create')
   * @returns {ComputedRef<boolean>}
   */
  const can = (permission) => {
    return computed(() => authStore.hasPermission(permission))
  }

  /**
   * Check if the current user has any of the specified permissions.
   * @param {string[]} permissions - Array of permissions to check
   * @returns {ComputedRef<boolean>}
   */
  const canAny = (...permissions) => {
    return computed(() => authStore.hasAnyPermission(permissions))
  }

  /**
   * Check if the current user has all of the specified permissions.
   * @param {string[]} permissions - Array of permissions to check
   * @returns {ComputedRef<boolean>}
   */
  const canAll = (...permissions) => {
    return computed(() => authStore.hasAllPermissions(permissions))
  }

  // =========================================================================
  // Role Checks
  // =========================================================================

  /** Current user is admin */
  const isAdmin = computed(() => authStore.isAdmin)

  /** Current user is designer (or admin) */
  const isDesigner = computed(() => authStore.isDesigner)

  /** Current user is operator (or admin) */
  const isOperator = computed(() => authStore.isOperator)

  /** User's role value (e.g., 'process_operator') */
  const role = computed(() => authStore.role)

  /** User's role display name (e.g., 'Process Operator') */
  const roleDisplay = computed(() => authStore.roleDisplay)

  /** All permissions the user has */
  const permissions = computed(() => authStore.permissions)

  /** Whether permissions have been loaded */
  const permissionsLoaded = computed(() => authStore.permissionsLoaded)

  // =========================================================================
  // Named Permission Checks (convenient shortcuts)
  // =========================================================================

  // Process permissions
  const canCreateProcess = computed(() => authStore.canCreateProcess)
  const canUpdateProcess = computed(() => authStore.canUpdateProcess)
  const canDeleteProcess = computed(() => authStore.canDeleteProcess)
  const canPublishProcess = computed(() => authStore.canPublishProcess)
  const canReadProcess = computed(() => authStore.hasPermission('process:read'))
  const canArchiveProcess = computed(() => authStore.hasPermission('process:archive'))

  // Execution permissions
  const canTriggerExecution = computed(() => authStore.canTriggerExecution)
  const canCancelExecution = computed(() => authStore.canCancelExecution)
  const canRetryExecution = computed(() => authStore.canRetryExecution)
  const canViewExecution = computed(() => authStore.hasPermission('execution:view'))

  // Approval permissions
  const canDecideApproval = computed(() => authStore.canDecideApproval)

  // Admin permissions
  const canViewAll = computed(() => authStore.hasPermission('admin:view_all'))
  const canManageUsers = computed(() => authStore.hasPermission('admin:manage_users'))

  // =========================================================================
  // Utility Functions
  // =========================================================================

  /**
   * Get a human-readable description of a permission.
   * @param {string} permission - Permission string
   * @returns {string}
   */
  const getPermissionDescription = (permission) => {
    const descriptions = {
      'process:create': 'Create new processes',
      'process:read': 'View processes',
      'process:update': 'Edit process definitions',
      'process:delete': 'Delete processes',
      'process:publish': 'Publish process versions',
      'process:archive': 'Archive processes',
      'execution:trigger': 'Start process executions',
      'execution:view': 'View execution results',
      'execution:cancel': 'Cancel running executions',
      'execution:retry': 'Retry failed executions',
      'approval:decide': 'Approve or reject pending items',
      'admin:view_all': 'View all resources across teams',
      'admin:manage_users': 'Manage user accounts and roles',
    }
    return descriptions[permission] || permission
  }

  /**
   * Get all permissions grouped by category.
   * @returns {Object} Permissions grouped by category
   */
  const getPermissionsByCategory = () => {
    const categories = {
      'Process': [],
      'Execution': [],
      'Approval': [],
      'Admin': []
    }

    for (const perm of permissions.value) {
      const [category] = perm.split(':')
      const categoryName = category.charAt(0).toUpperCase() + category.slice(1)
      if (categories[categoryName]) {
        categories[categoryName].push({
          value: perm,
          description: getPermissionDescription(perm)
        })
      }
    }

    return categories
  }

  return {
    // Core checks
    can,
    canAny,
    canAll,

    // Role checks
    isAdmin,
    isDesigner,
    isOperator,
    role,
    roleDisplay,
    permissions,
    permissionsLoaded,

    // Named permission checks - Process
    canCreateProcess,
    canReadProcess,
    canUpdateProcess,
    canDeleteProcess,
    canPublishProcess,
    canArchiveProcess,

    // Named permission checks - Execution
    canTriggerExecution,
    canViewExecution,
    canCancelExecution,
    canRetryExecution,

    // Named permission checks - Approval
    canDecideApproval,

    // Named permission checks - Admin
    canViewAll,
    canManageUsers,

    // Utilities
    getPermissionDescription,
    getPermissionsByCategory
  }
}
