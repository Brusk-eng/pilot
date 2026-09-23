import { apiUrl, request, unwrap } from '@/api/client'
import type { DisabledApp, EnabledApp, SiteApps } from '@/types/siteApps'
import type { Backup, BackupSchedule } from '@/types/siteBackups'
import type { DnsRecords, SiteDomains } from '@/types/siteDomains'
import type { SiteAnalytics, SiteUptime } from '@/types/siteMonitoring'
import type { SiteStorageReport } from '@/types/siteStorage'
import type {
  MigrationStarted,
  SiteDetail,
  SiteLoginLink,
  SiteResource,
  WildcardDomains,
} from '@/types/sites'
import type { TaskPayload } from '@/types/tasks'

type SiteConfig = Record<string, unknown>

// App install and remove answer inline for a disabled app, so they wait on frappe.
const inlineTimeout = 120_000

export const sitesApi = {
  list: () => request.get('sites').json<SiteResource[]>(),
  // The report the site-storage timer refreshes; measuring again is a task.

  // The report the site-storage timer refreshes; measuring again is a task.
  storage: () => request.get('sites/storage').json<SiteStorageReport>(),

  refreshStorage: (name: string) =>
    request.post(`sites/${encodeURIComponent(name)}/actions/refresh-storage`).json<TaskPayload>(),

  detail: (name: string) => request.get(`sites/${encodeURIComponent(name)}`).json<SiteDetail>(),

  create: (payload: Record<string, unknown>) =>
    request.post('sites', { json: payload }).json<TaskPayload>(),

  loginLink: (name: string) =>
    request.post(`sites/${encodeURIComponent(name)}/login`).json<SiteLoginLink>(),

  configuration: {
    get: (name: string) =>
      unwrap(request.get(`sites/${encodeURIComponent(name)}/configuration`).json<SiteConfig>()),
    update: (name: string, patch: SiteConfig) =>
      unwrap(
        request
          .patch(`sites/${encodeURIComponent(name)}/configuration`, { json: patch })
          .json<SiteConfig>(),
      ),
  },

  enableTls: (name: string, email?: string) =>
    request
      .post(`sites/${encodeURIComponent(name)}/actions/enable-tls`, {
        json: email ? { email } : {},
      })
      .json<TaskPayload>(),

  clearCache: (name: string) =>
    request.post(`sites/${encodeURIComponent(name)}/actions/clear-cache`).json<TaskPayload>(),

  migrate: (name: string) =>
    request.post(`sites/${encodeURIComponent(name)}/actions/migrate`).json<MigrationStarted>(),

  reinstall: (name: string) =>
    request.post(`sites/${encodeURIComponent(name)}/actions/reinstall`).json<TaskPayload>(),

  drop: (name: string) => request.delete(`sites/${encodeURIComponent(name)}`).json<TaskPayload>(),

  apps: {
    list: (name: string) => request.get(`sites/${encodeURIComponent(name)}/apps`).json<SiteApps>(),
    install: (name: string, payload: Record<string, unknown>) =>
      request
        .post(`sites/${encodeURIComponent(name)}/apps`, { json: payload, timeout: inlineTimeout })
        .json<EnabledApp | TaskPayload>(),
    remove: (
      name: string,
      app: string,
      { force = false, mode = '' }: { force?: boolean; mode?: string } = {},
    ) =>
      request
        .delete(`sites/${encodeURIComponent(name)}/apps/${encodeURIComponent(app)}`, {
          searchParams: { ...(force ? { force: 'true' } : {}), ...(mode ? { mode } : {}) },
          timeout: inlineTimeout,
        })
        .json<DisabledApp | TaskPayload>(),
  },

  domains: {
    list: (name: string) =>
      request.get(`sites/${encodeURIComponent(name)}/domains`).json<SiteDomains>(),
    add: (name: string, domain: string) =>
      request
        .post(`sites/${encodeURIComponent(name)}/domains`, { json: { domain } })
        .json<TaskPayload>(),
    remove: (name: string, domain: string) =>
      request
        .delete(`sites/${encodeURIComponent(name)}/domains/${encodeURIComponent(domain)}`)
        .json<TaskPayload>(),
    setPrimary: (name: string, domain: string) =>
      request
        .patch(`sites/${encodeURIComponent(name)}/domains/${encodeURIComponent(domain)}`, {
          json: { primary: true },
        })
        .json<TaskPayload>(),
    dnsRecords: (name: string, domain: string) =>
      request
        .get(`sites/${encodeURIComponent(name)}/domains/${encodeURIComponent(domain)}/dns-records`)
        .json<DnsRecords>(),
    wildcardList: () => request.get('sites/wildcard-domains').json<WildcardDomains>(),
  },

  monitoring: {
    get: (name: string, window: string) =>
      request
        .get(`sites/${encodeURIComponent(name)}/monitoring`, { searchParams: { window } })
        .json<SiteAnalytics>(),
  },

  uptime: {
    get: (name: string, window: string) =>
      request
        .get(`sites/${encodeURIComponent(name)}/uptime`, { searchParams: { window } })
        .json<SiteUptime>(),
  },

  backups: {
    list: (name: string, limit?: number) =>
      request
        .get(`sites/${encodeURIComponent(name)}/backups`, { searchParams: limit ? { limit } : {} })
        .json<Backup[]>(),
    create: (name: string) =>
      request.post(`sites/${encodeURIComponent(name)}/backups`).json<TaskPayload>(),
    download: (name: string, timestamp: string, fileId: string): string =>
      apiUrl(
        `sites/${encodeURIComponent(name)}/backups/${encodeURIComponent(timestamp)}/files/${encodeURIComponent(fileId)}/content`,
      ),
    downloadLinks: (name: string, timestamp: string) =>
      request
        .get(
          `sites/${encodeURIComponent(name)}/backups/${encodeURIComponent(timestamp)}/download-links`,
        )
        .json<Record<string, string>>(),
    schedule: {
      get: (name: string) =>
        request.get(`sites/${encodeURIComponent(name)}/backup-schedule`).json<BackupSchedule>(),
      set: (name: string, payload: Record<string, unknown>) =>
        request
          .put(`sites/${encodeURIComponent(name)}/backup-schedule`, { json: payload })
          .json<BackupSchedule>(),
      remove: (name: string) => request.delete(`sites/${encodeURIComponent(name)}/backup-schedule`),
    },
  },
}
