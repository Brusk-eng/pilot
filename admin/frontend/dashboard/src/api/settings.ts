import { request, unwrap } from '@/api/client'
import type { ClientAddress, Settings, SettingsUpdate } from '@/types/settings'
import type { CliDevUpdate, CliReleaseUpdate } from '@/types/updates'

export type CliUpdate = CliDevUpdate | CliReleaseUpdate

export const settingsApi = {
  get: () => unwrap(request.get('settings').json<Settings>()),

  update: (data: Record<string, unknown>) =>
    unwrap(request.patch('settings', { json: data }).json<SettingsUpdate>()),

  changeAdminPassword: (data: Record<string, unknown>) =>
    unwrap(request.post('auth/password', { json: data }).json<Record<string, never>>()),

  myIp: () => request.get('network/client').json<ClientAddress>(),

  llmModels: (provider: string, apiKey = '', apiBase = '') =>
    request
      .post('settings/llm/models', { json: { provider, api_key: apiKey, api_base: apiBase } })
      .json<string[]>(),
}

export const cliUpdatesApi = {
  status: () => unwrap(request.get('cli-updates').json<CliUpdate>()),
  check: () => unwrap(request.post('cli-update-checks').json<CliUpdate>()),
}
