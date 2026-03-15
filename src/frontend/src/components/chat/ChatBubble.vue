<template>
  <!-- User message (plain text) -->
  <div
    v-if="role === 'user'"
    class="max-w-[85%] ml-auto"
  >
    <div class="rounded-xl px-4 py-3 bg-indigo-600 text-white">
      <p class="whitespace-pre-wrap">{{ content }}</p>
    </div>
    <p v-if="formattedTime" class="text-xs text-gray-400 dark:text-gray-500 mt-1 text-right">{{ formattedTime }}</p>
  </div>
  <!-- Assistant message (markdown rendered) -->
  <div
    v-else
    class="max-w-[85%]"
  >
    <div class="rounded-xl px-4 py-3 bg-white dark:bg-gray-800 text-gray-900 dark:text-white shadow-sm">
      <div
        class="prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-headings:my-3 prose-ul:my-2 prose-ol:my-2 prose-li:my-0 prose-pre:my-2 prose-code:text-indigo-600 dark:prose-code:text-indigo-400 prose-code:bg-gray-100 dark:prose-code:bg-gray-700 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none"
        v-html="renderedContent"
      ></div>
    </div>
    <p v-if="formattedTime" class="text-xs text-gray-400 dark:text-gray-500 mt-1">{{ formattedTime }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '../../utils/markdown'

const props = defineProps({
  role: {
    type: String,
    required: true,
    validator: (value) => ['user', 'assistant'].includes(value)
  },
  content: {
    type: String,
    required: true
  },
  timestamp: {
    type: String,
    default: null
  }
})

const renderedContent = computed(() => {
  return renderMarkdown(props.content)
})

const formattedTime = computed(() => {
  if (!props.timestamp) return null
  const date = new Date(props.timestamp)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  const time = date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
  if (isToday) return time
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) + ', ' + time
})
</script>
