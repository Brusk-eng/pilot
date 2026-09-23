import { apiUrl, request } from '@/api/client'
import type { LogFile, LogTail } from '@/types/logs'

export const logsApi = {
  list: () => request.get('logs').json<LogFile[]>(),

  read: (filename: string, lines: number) =>
    request
      .get(`logs/${encodeURIComponent(filename)}`, { searchParams: { lines } })
      .json<LogTail>(),

  streamUrl: (filename: string) => apiUrl(`logs/${encodeURIComponent(filename)}/events`),
  downloadUrl: (filename: string) => apiUrl(`logs/${encodeURIComponent(filename)}/content`),
}
