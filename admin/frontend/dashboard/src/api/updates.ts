import { request } from '@/api/client'
import type { MigrationAccepted, MigrationPage, MigrationSummary } from '@/types/migrations'
import { ACTIVE_STATES, ATTENTION_STATES } from '@/utils/updateFormat.ts'

type Operation = MigrationSummary | null | undefined

export const updatesApi = {
  list: (params: Record<string, string | number> = {}) =>
    request.get('migrations', { searchParams: params }).json<MigrationPage>(),

  current: () => request.get('migrations/current').json<MigrationSummary | null>(),
  detail: (id: string) => request.get(`migrations/${id}`).json<MigrationSummary>(),

  createUpdate: (json: Record<string, unknown> = {}) =>
    request.post('updates', { json }).json<MigrationAccepted>(),

  retry: (id: string) => request.post(`migrations/${id}/actions/retry`).json<MigrationAccepted>(),

  restore: (id: string) =>
    request.post(`migrations/${id}/actions/restore`).json<MigrationAccepted>(),

  bypassPatch: (id: string, patch: string) =>
    request
      .post(`migrations/${id}/actions/bypass-patch`, { json: { patch } })
      .json<MigrationAccepted>(),
}

export const isResolved = (operation: Operation) => {
  return !operation || operation.state === 'completed' || operation.state === 'reverted'
}

export const needsAttention = (operation: Operation) => {
  return !!operation && ATTENTION_STATES.includes(operation.state)
}

export const isActive = (operation: Operation) => {
  return !!operation && ACTIVE_STATES.includes(operation.state)
}

export const isPending = (operation: Operation) => {
  return !!operation?.pending_action
}
