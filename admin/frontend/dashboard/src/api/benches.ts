import { request } from '@/api/client'
import type { BenchReadiness, BenchResource, CreatedBench } from '@/types/benches'
import type { WildcardDomains } from '@/types/sites'

export const benchesApi = {
  list: () => request.get('benches').json<BenchResource[]>(),

  start: (name: string) =>
    request.post(`benches/${encodeURIComponent(name)}/actions/start`).json<BenchResource>(),

  stop: (name: string) =>
    request.post(`benches/${encodeURIComponent(name)}/actions/stop`).json<BenchResource>(),

  restart: (name: string) =>
    request.post(`benches/${encodeURIComponent(name)}/actions/restart`).json<BenchResource>(),

  drop: (name: string) => request.delete(`benches/${encodeURIComponent(name)}`),

  create: (payload: Record<string, unknown>) =>
    request.post('benches', { json: payload }).json<CreatedBench>(),

  wildcardDomains: () => request.get('benches/domain-options').json<WildcardDomains>(),

  ready: (payload: Record<string, unknown>) =>
    request.post('bench-readiness-checks', { json: payload }).json<BenchReadiness>(),
}
