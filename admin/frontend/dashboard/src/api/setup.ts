import { apiUrl, request } from '@/api/client'
import type { Bootstrap } from '@/types/core'
import type { DatabaseValidation, FrameworkBranches, SetupConfiguration } from '@/types/setup'
import type { TaskPayload } from '@/types/tasks'

const setupIdempotencyKey = 'wizard-setup'

export const setupApi = {
  bootstrap: () => request.get('bootstrap').json<Bootstrap>(),
  config: () => request.get('setup/configuration').json<SetupConfiguration>(),
  branches: () => request.get('setup/framework-branches').json<FrameworkBranches>(),

  validateDatabase: (json: Record<string, unknown>) =>
    request.post('setup/database-validations', { json }).json<DatabaseValidation>(),

  save: (json: Record<string, unknown>) =>
    request.put('setup/configuration', { json }).json<SetupConfiguration>(),

  start: () =>
    request
      .post('setup/actions/start', {
        headers: { 'Idempotency-Key': setupIdempotencyKey },
      })
      .json<TaskPayload>(),

  finish: (taskId: string) => request.post('setup/actions/finish', { json: { task_id: taskId } }),
  streamUrl: (taskId: string) => apiUrl(`tasks/${taskId}/events`),
}
