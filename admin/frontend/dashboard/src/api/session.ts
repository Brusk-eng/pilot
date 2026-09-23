import { request, unwrap } from '@/api/client'
import type { ActiveSessions, RevokedSessions } from '@/types/auth'

export const sessionApi = {
  list: () => unwrap(request.get('auth/sessions').json<ActiveSessions>()),
  revoke: (jti: string) => request.post(`auth/sessions/revoke/${jti}`),
  revokeAll: () => unwrap(request.post('auth/sessions/revoke/all').json<RevokedSessions>()),
}
