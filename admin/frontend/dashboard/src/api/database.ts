import { request } from '@/api/client'
import type {
  ActionStatus,
  BinlogFile,
  DatabaseCapabilities,
  DatabaseConfigurationSnapshot,
  DatabaseDiagnostics,
  DatabaseProcess,
  DatabaseSite,
  DatabaseSize,
  ExecutedQuery,
  LockWaitRow,
  PerformanceSection,
  TableSchema,
  TableSize,
  UnsupportedDatabaseDiagnostics,
} from '@/types/database'
import type { TaskPayload } from '@/types/tasks'

export const databaseApi = {
  sites: () => request.get('database/sites').json<DatabaseSite[]>(),

  schema: (site: string) =>
    request.get('database/schema', { searchParams: { site } }).json<TableSchema[]>(),

  execute: (site: string, query: string, readOnly: boolean) =>
    request
      .post('database/queries', { json: { site, query, read_only: readOnly } })
      .json<ExecutedQuery>(),

  diagnostics: () =>
    request
      .get('database/diagnostics')
      .json<DatabaseDiagnostics | UnsupportedDatabaseDiagnostics>(),

  processList: (site = '') =>
    request
      .get('database/processlist', { searchParams: site ? { site } : {} })
      .json<DatabaseProcess[]>(),

  lockWaitRows: (site = '') =>
    request.get('database/lockwaits', { searchParams: site ? { site } : {} }).json<LockWaitRow[]>(),

  size: (site = '') =>
    request.get('database/size', { searchParams: site ? { site } : {} }).json<DatabaseSize>(),

  tableSizes: (site: string) =>
    request.get('database/table-sizes', { searchParams: { site } }).json<TableSize[]>(),

  performanceReport: (reportType: string, site = '', limit = 20, offset = 0) =>
    request
      .get('database/performance-report', {
        searchParams: { report_type: reportType, site, limit, offset },
      })
      .json<PerformanceSection>(),

  killProcess: (processId: number) =>
    request
      .post('database/processlist/kill', { json: { process_id: processId } })
      .json<ActionStatus>(),

  binlogs: {
    list: () => request.get('database/binlogs').json<BinlogFile[]>(),
    purge: (upTo: string) =>
      request.post('database/binlogs/purge', { json: { up_to: upTo } }).json<ActionStatus>(),
  },

  configurations: {
    list: () => request.get('database/configurations').json<DatabaseConfigurationSnapshot>(),
    set: (variable: string, value: unknown, idempotencyKey: string) =>
      request
        .post(`database/configurations/${encodeURIComponent(variable)}`, {
          json: { value },
          headers: { 'Idempotency-Key': idempotencyKey },
        })
        .json<TaskPayload>(),
  },

  quickActions: {
    capabilities: () => request.get('database/quick-actions').json<DatabaseCapabilities>(),
    restart: (idempotencyKey: string) =>
      request
        .post('database/quick-actions/restart', {
          headers: { 'Idempotency-Key': idempotencyKey },
        })
        .json<TaskPayload>(),
    setPerformanceSchema: (enabled: boolean, idempotencyKey: string) =>
      request
        .post('database/quick-actions/performance-schema', {
          json: { enabled },
          headers: { 'Idempotency-Key': idempotencyKey },
        })
        .json<TaskPayload>(),
    setInnoDBBufferPoolSize: (sizeMb: number, idempotencyKey: string) =>
      request
        .post('database/quick-actions/innodb-buffer-pool-size', {
          json: { size_mb: sizeMb },
          headers: { 'Idempotency-Key': idempotencyKey },
        })
        .json<TaskPayload>(),
    setMaxConnections: (maxConnections: number, idempotencyKey: string) =>
      request
        .post('database/quick-actions/max-connections', {
          json: { max_connections: maxConnections },
          headers: { 'Idempotency-Key': idempotencyKey },
        })
        .json<TaskPayload>(),
  },
}
