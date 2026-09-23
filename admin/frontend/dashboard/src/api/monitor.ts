import { request } from '@/api/client'
import type {
  DatabaseHistory,
  SystemHistory,
  SystemInfo,
  SystemMetrics,
  WafAnalytics,
} from '@/types/stats'
import type { StorageBreakdown } from '@/types/storage'

export const monitorApi = {
  stats: () => request.get('metrics').json<SystemMetrics>(),

  history: (window: string) =>
    request.get('monitor/history', { searchParams: { window } }).json<SystemHistory>(),

  dbHistory: (window: string) =>
    request.get('database/history', { searchParams: { window } }).json<DatabaseHistory>(),

  systemInfo: () => request.get('system').json<SystemInfo>(),
  waf: (window: string) => request.get('waf', { searchParams: { window } }).json<WafAnalytics>(),
  storage: () => request.get('storage').json<StorageBreakdown>(),
}
