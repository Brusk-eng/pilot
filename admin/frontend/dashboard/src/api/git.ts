import { request } from '@/api/client'
import type { GitBranches, GitConnection, GitRepository, ResolvedApp } from '@/types/git'

export const gitApi = {
  status: () => request.get('git/connection').json<GitConnection>(),
  connect: (provider: string, token: string, username: string) =>
    request.put('git/connection', { json: { provider, token, username } }).json<GitConnection>(),
  disconnect: () => request.delete('git/connection'),
  repos: () => request.get('git/repositories').json<GitRepository[]>(),
  branches: (repo: string) =>
    request.get('git/branches', { searchParams: { repo } }).json<GitBranches>(),
  resolve: (repo: string, branch?: string) =>
    request
      .post('git/repository-resolutions', { json: { repo, branch: branch || '' } })
      .json<ResolvedApp>(),
}
