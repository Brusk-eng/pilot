import { request, unwrap } from '@/api/client'
import type { AppInfo, MarketplaceApp } from '@/types/apps'
import type { TaskPayload } from '@/types/tasks'

export const appsApi = {
  marketplace: () => unwrap(request.get('marketplace/apps').json<MarketplaceApp[]>()),
  installed: () => unwrap(request.get('apps').json<AppInfo[]>()),
  fetchUpdates: () => request.post('apps/fetch').json<TaskPayload>(),

  add: (payload: Record<string, unknown>) =>
    request.post('apps', { json: payload }).json<TaskPayload>(),
}
