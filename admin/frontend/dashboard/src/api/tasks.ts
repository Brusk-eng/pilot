import { apiUrl, request } from '@/api/client'
import type { TaskPayload, TaskWorker } from '@/types/tasks'

export const tasksApi = {
  list: (status?: string) =>
    request
      .get('tasks', status && status !== 'all' ? { searchParams: { status } } : {})
      .json<TaskPayload[]>(),

  detail: (taskId: string) => request.get(`tasks/${taskId}`).json<TaskPayload>(),

  run: (command: string, args: Record<string, unknown> = {}) =>
    request.post('tasks', { json: { command, ...args } }).json<TaskPayload>(),

  cancel: (taskId: string) => request.delete(`tasks/${taskId}`),
  retry: (taskId: string) => request.post(`tasks/${taskId}/actions/retry`).json<TaskPayload>(),

  output: async (taskId: string) => {
    const response = await request.get(`tasks/${taskId}/output/content`)
    return response.ok ? response.text() : ''
  },

  outputUrl: (taskId: string) => apiUrl(`tasks/${taskId}/output/content`),
  streamUrl: (taskId: string) => apiUrl(`tasks/${taskId}/events`),

  debugUrl: (taskId: string, refresh = false) =>
    apiUrl(`tasks/${taskId}/debug${refresh ? '?refresh=1' : ''}`),
}

export const taskWorkerApi = {
  detail: () => request.get('task-worker').json<TaskWorker>(),
  start: () => request.post('task-worker/actions/start').json<TaskWorker>(),
  stop: () => request.post('task-worker/actions/stop').json<TaskWorker>(),
}
