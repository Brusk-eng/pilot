import { request } from '@/api/client'
import type { AdminSession } from '@/types/auth'
import type { Bootstrap } from '@/types/core'

export const authApi = {
  bootstrap: () => request.get('bootstrap').json<Bootstrap>(),
  session: () => request.get('auth/session').json<AdminSession>(),

  login: (password: string, otp?: string) =>
    request.post('auth/session', { json: { password, otp } }).json<AdminSession>(),

  loginWithSid: (sid: string) =>
    request.post('auth/session', { json: { sid } }).json<AdminSession>(),

  logout: () => request.delete('auth/session'),
}
