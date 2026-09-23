import { request, unwrap } from '@/api/client'
import type { RecoveryCodes, TwoFactorEnrollment, TwoFactorStatus } from '@/types/auth'

// The device name is the key, so it has to be encoded for the URL path.
const path = (name: string) => `auth/two-factor/${encodeURIComponent(name)}`

export const twoFactorApi = {
  status: () => unwrap(request.get('auth/two-factor').json<TwoFactorStatus>()),

  startEnrollment: (name: string) =>
    unwrap(
      request.post('auth/two-factor/enrollment', { json: { name } }).json<TwoFactorEnrollment>(),
    ),

  confirm: (name: string, otp: string) =>
    unwrap(request.post(path(name), { json: { otp } }).json<TwoFactorStatus>()),

  removeDevice: (name: string) => unwrap(request.delete(path(name)).json<TwoFactorStatus>()),

  regenerateRecoveryCodes: () =>
    unwrap(request.post('auth/two-factor/recovery-codes').json<RecoveryCodes>()),
}
