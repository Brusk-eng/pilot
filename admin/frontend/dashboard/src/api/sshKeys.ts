import { request } from '@/api/client'
import type { AuthorizedSSHKey, AuthorizedSSHKeys } from '@/types/sshKeys'

export const sshKeysApi = {
  list: () => request.get('ssh-keys').json<AuthorizedSSHKeys>(),

  add: (public_key: string) =>
    request.post('ssh-keys', { json: { public_key } }).json<AuthorizedSSHKey>(),

  remove: (fingerprint: string) => request.delete(`ssh-keys/${encodeURIComponent(fingerprint)}`),
}
