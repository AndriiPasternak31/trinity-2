<template>
  <!-- Hide mode: Don't render anything if no permission -->
  <template v-if="fallbackMode === 'hide'">
    <slot v-if="hasPermission" />
  </template>

  <!-- Disable mode: Render but disable if no permission -->
  <template v-else-if="fallbackMode === 'disable'">
    <div
      :class="{ 'opacity-50 cursor-not-allowed pointer-events-none': !hasPermission }"
      :title="!hasPermission ? tooltip : undefined"
    >
      <slot :disabled="!hasPermission" />
    </div>
  </template>

  <!-- Tooltip mode: Render with tooltip explaining why disabled -->
  <template v-else-if="fallbackMode === 'tooltip'">
    <div
      class="relative inline-block"
      @mouseenter="showTooltip = !hasPermission"
      @mouseleave="showTooltip = false"
    >
      <div :class="{ 'opacity-50 cursor-not-allowed pointer-events-none': !hasPermission }">
        <slot :disabled="!hasPermission" />
      </div>
      <!-- Tooltip -->
      <Transition
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-1"
        enter-to-class="opacity-100 translate-y-0"
        leave-active-class="transition ease-in duration-150"
        leave-from-class="opacity-100 translate-y-0"
        leave-to-class="opacity-0 translate-y-1"
      >
        <div
          v-if="showTooltip"
          class="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 text-sm text-white bg-gray-900 dark:bg-gray-700 rounded-lg shadow-lg whitespace-nowrap"
        >
          {{ tooltip }}
          <div class="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700"></div>
        </div>
      </Transition>
    </div>
  </template>

  <!-- Default: Same as hide -->
  <template v-else>
    <slot v-if="hasPermission" />
  </template>
</template>

<script setup>
/**
 * PermissionGuard Component
 *
 * Conditionally renders or disables content based on user permissions.
 *
 * Reference: BACKLOG_ACCESS_AUDIT.md - E17-09
 *
 * @example
 * <!-- Hide if no permission -->
 * <PermissionGuard permission="process:create">
 *   <button>Create Process</button>
 * </PermissionGuard>
 *
 * <!-- Disable if no permission -->
 * <PermissionGuard permission="process:update" fallback="disable">
 *   <template #default="{ disabled }">
 *     <button :disabled="disabled">Save</button>
 *   </template>
 * </PermissionGuard>
 *
 * <!-- Multiple permissions (any) -->
 * <PermissionGuard :permissions="['process:update', 'process:publish']" match="any">
 *   <button>Edit</button>
 * </PermissionGuard>
 */

import { ref, computed } from 'vue'
import { usePermissions } from '@/composables/usePermissions'

const props = defineProps({
  /**
   * Single permission to check (e.g., 'process:create')
   */
  permission: {
    type: String,
    default: null
  },

  /**
   * Multiple permissions to check
   */
  permissions: {
    type: Array,
    default: () => []
  },

  /**
   * How to match multiple permissions: 'any' or 'all'
   */
  match: {
    type: String,
    default: 'any',
    validator: (v) => ['any', 'all'].includes(v)
  },

  /**
   * What to do when permission is denied:
   * - 'hide': Don't render the content (default)
   * - 'disable': Render but disable interaction
   * - 'tooltip': Render with tooltip explaining why disabled
   */
  fallback: {
    type: String,
    default: 'hide',
    validator: (v) => ['hide', 'disable', 'tooltip'].includes(v)
  },

  /**
   * Custom tooltip message when permission is denied
   */
  tooltip: {
    type: String,
    default: 'You do not have permission to perform this action'
  },

  /**
   * Require admin role instead of specific permission
   */
  requireAdmin: {
    type: Boolean,
    default: false
  }
})

const { can, canAny, canAll, isAdmin } = usePermissions()

const showTooltip = ref(false)

const fallbackMode = computed(() => props.fallback)

const hasPermission = computed(() => {
  // Admin requirement check
  if (props.requireAdmin) {
    return isAdmin.value
  }

  // Single permission check
  if (props.permission) {
    return can(props.permission).value
  }

  // Multiple permissions check
  if (props.permissions.length > 0) {
    if (props.match === 'all') {
      return canAll(...props.permissions).value
    } else {
      return canAny(...props.permissions).value
    }
  }

  // No permission specified - allow by default
  return true
})
</script>
