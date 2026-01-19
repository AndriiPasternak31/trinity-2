<template>
  <div class="min-h-screen bg-gray-100 dark:bg-gray-900 py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center gap-3 mb-2">
          <UsersIcon class="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
          <h1 class="text-3xl font-bold text-gray-900 dark:text-white">User Management</h1>
        </div>
        <p class="text-gray-600 dark:text-gray-400">Manage user roles and permissions</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <span class="ml-3 text-gray-600 dark:text-gray-400">Loading users...</span>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 rounded-lg p-6">
        <div class="flex items-center gap-3">
          <ExclamationCircleIcon class="h-6 w-6 text-red-600 dark:text-red-400" />
          <div>
            <h3 class="text-lg font-medium text-red-800 dark:text-red-200">Access Denied</h3>
            <p class="text-red-700 dark:text-red-300">{{ error }}</p>
          </div>
        </div>
      </div>

      <!-- Main Content -->
      <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Users Table -->
        <div class="lg:col-span-2 bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Users ({{ users.length }})</h2>
          </div>
          
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead class="bg-gray-50 dark:bg-gray-900/50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">User</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Role</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Last Login</th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-200 dark:divide-gray-700">
                <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td class="px-6 py-4 whitespace-nowrap">
                    <div class="flex items-center gap-3">
                      <div class="h-10 w-10 rounded-full bg-indigo-100 dark:bg-indigo-900/50 flex items-center justify-center">
                        <span class="text-sm font-medium text-indigo-600 dark:text-indigo-400">
                          {{ getUserInitials(user) }}
                        </span>
                      </div>
                      <div>
                        <div class="text-sm font-medium text-gray-900 dark:text-white">{{ user.name || user.username }}</div>
                        <div class="text-sm text-gray-500 dark:text-gray-400">{{ user.email || '-' }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap">
                    <select
                      v-model="user.role"
                      @change="updateUserRole(user)"
                      :disabled="isCurrentUser(user) || updating === user.id"
                      class="text-sm rounded-lg border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <option v-for="role in availableRoles" :key="role.value" :value="role.value">
                        {{ role.name }}
                      </option>
                    </select>
                    <span v-if="isCurrentUser(user)" class="ml-2 text-xs text-gray-500 dark:text-gray-400">(you)</span>
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                    {{ formatDate(user.last_login) }}
                  </td>
                  <td class="px-6 py-4 whitespace-nowrap text-right text-sm">
                    <button
                      v-if="!isCurrentUser(user)"
                      @click="showPermissions(user)"
                      class="text-indigo-600 dark:text-indigo-400 hover:text-indigo-900 dark:hover:text-indigo-300"
                    >
                      View Permissions
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          
          <!-- Empty State -->
          <div v-if="users.length === 0" class="p-8 text-center">
            <UsersIcon class="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <p class="text-gray-500 dark:text-gray-400">No users found</p>
          </div>
        </div>

        <!-- Role Reference Panel -->
        <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden">
          <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white">Role Reference</h2>
          </div>
          <div class="p-6 space-y-4">
            <div v-for="role in availableRoles" :key="role.value" class="border-b border-gray-100 dark:border-gray-700 pb-4 last:border-0">
              <div class="flex items-center justify-between mb-2">
                <span class="font-medium text-gray-900 dark:text-white">{{ role.name }}</span>
                <span class="text-xs text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                  {{ role.permission_count }} permissions
                </span>
              </div>
              <p class="text-sm text-gray-600 dark:text-gray-400">{{ role.description }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Permission Modal -->
      <Teleport to="body">
        <div v-if="selectedUser" class="fixed inset-0 z-50 flex items-center justify-center p-4" @click.self="selectedUser = null">
          <div class="fixed inset-0 bg-black/50 backdrop-blur-sm"></div>
          <div class="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-lg w-full max-h-[80vh] overflow-hidden">
            <div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h3 class="text-lg font-semibold text-gray-900 dark:text-white">{{ selectedUser.name || selectedUser.username }}</h3>
                <p class="text-sm text-gray-500 dark:text-gray-400">{{ getRoleDisplay(selectedUser.role) }} Permissions</p>
              </div>
              <button @click="selectedUser = null" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                <XMarkIcon class="h-6 w-6" />
              </button>
            </div>
            <div class="p-6 overflow-y-auto max-h-[60vh]">
              <div v-for="(perms, category) in getPermissionsForRole(selectedUser.role)" :key="category" class="mb-6 last:mb-0">
                <h4 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 uppercase tracking-wide">{{ category }}</h4>
                <div class="space-y-2">
                  <div v-for="perm in perms" :key="perm" class="flex items-center gap-2">
                    <CheckCircleIcon class="h-5 w-5 text-green-500" />
                    <span class="text-sm text-gray-600 dark:text-gray-400">{{ perm }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Success Toast -->
      <Teleport to="body">
        <Transition
          enter-active-class="transition ease-out duration-300"
          enter-from-class="opacity-0 translate-y-2"
          enter-to-class="opacity-100 translate-y-0"
          leave-active-class="transition ease-in duration-200"
          leave-from-class="opacity-100 translate-y-0"
          leave-to-class="opacity-0 translate-y-2"
        >
          <div v-if="successMessage" class="fixed bottom-4 right-4 z-50 bg-green-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-2">
            <CheckCircleIcon class="h-5 w-5" />
            <span>{{ successMessage }}</span>
          </div>
        </Transition>
      </Teleport>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import {
  UsersIcon,
  ExclamationCircleIcon,
  XMarkIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline'

const authStore = useAuthStore()

const users = ref([])
const availableRoles = ref([])
const loading = ref(true)
const error = ref(null)
const updating = ref(null)
const selectedUser = ref(null)
const successMessage = ref(null)

// Permission mapping for display
const ROLE_PERMISSIONS = {
  'process_admin': {
    Process: ['Create', 'Read', 'Update', 'Delete', 'Publish', 'Archive'],
    Execution: ['Trigger', 'View', 'Cancel', 'Retry'],
    Approval: ['Decide'],
    Admin: ['View All Resources', 'Manage Users']
  },
  'process_designer': {
    Process: ['Create', 'Read', 'Update', 'Delete', 'Publish'],
    Execution: ['View'],
    Approval: []
  },
  'process_operator': {
    Process: ['Read'],
    Execution: ['Trigger', 'View', 'Cancel', 'Retry'],
    Approval: []
  },
  'process_viewer': {
    Process: ['Read'],
    Execution: ['View'],
    Approval: []
  },
  'process_approver': {
    Process: ['Read'],
    Execution: ['View'],
    Approval: ['Decide']
  }
}

onMounted(async () => {
  await loadUsers()
  await loadRoles()
})

async function loadUsers() {
  loading.value = true
  error.value = null
  
  try {
    const response = await axios.get('/api/admin/users', {
      headers: authStore.authHeader
    })
    users.value = response.data.users
  } catch (err) {
    console.error('Failed to load users:', err)
    if (err.response?.status === 403) {
      error.value = 'You do not have permission to manage users. Admin access required.'
    } else {
      error.value = err.response?.data?.detail || 'Failed to load users'
    }
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  try {
    const response = await axios.get('/api/admin/users/roles/available', {
      headers: authStore.authHeader
    })
    availableRoles.value = response.data.roles
  } catch (err) {
    console.error('Failed to load roles:', err)
    // Fallback to hardcoded roles
    availableRoles.value = [
      { value: 'process_admin', name: 'Admin', description: 'Full access', permission_count: 13 },
      { value: 'process_designer', name: 'Designer', description: 'Create and edit processes', permission_count: 6 },
      { value: 'process_operator', name: 'Operator', description: 'Run and manage executions', permission_count: 5 },
      { value: 'process_viewer', name: 'Viewer', description: 'Read-only access', permission_count: 2 },
      { value: 'process_approver', name: 'Approver', description: 'Handle approvals', permission_count: 3 }
    ]
  }
}

async function updateUserRole(user) {
  updating.value = user.id
  
  try {
    await axios.put(`/api/admin/users/${user.id}/role`, {
      role: user.role
    }, {
      headers: authStore.authHeader
    })
    
    showSuccess(`Updated ${user.name || user.username}'s role`)
  } catch (err) {
    console.error('Failed to update role:', err)
    // Reload to get correct role back
    await loadUsers()
  } finally {
    updating.value = null
  }
}

function getUserInitials(user) {
  const name = user.name || user.username || '?'
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}

function isCurrentUser(user) {
  return user.username === authStore.user?.name || user.email === authStore.user?.email
}

function getRoleDisplay(role) {
  const r = availableRoles.value.find(r => r.value === role)
  return r?.name || role
}

function formatDate(dateStr) {
  if (!dateStr) return 'Never'
  const date = new Date(dateStr)
  return date.toLocaleDateString(undefined, { 
    month: 'short', 
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function showPermissions(user) {
  selectedUser.value = user
}

function getPermissionsForRole(role) {
  const perms = ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS['process_viewer']
  // Filter out empty categories
  const filtered = {}
  for (const [category, items] of Object.entries(perms)) {
    if (items.length > 0) {
      filtered[category] = items
    }
  }
  return filtered
}

function showSuccess(message) {
  successMessage.value = message
  setTimeout(() => {
    successMessage.value = null
  }, 3000)
}
</script>
