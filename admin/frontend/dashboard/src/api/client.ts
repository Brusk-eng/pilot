import ky from 'ky'

import { isSignedOut, reportSignedOut } from '@/composables/auth/useSignedOut'
import type { ErrorResponse } from '@/types/common'

export type ApiErrorPayload = Partial<ErrorResponse> | { error?: string } | null | undefined

export const API_V1_PREFIX = '/api/v1'

export const apiUrl = (path = '', origin = ''): string => {
  const suffix = path ? `/${String(path).replace(/^\/+/, '')}` : ''
  return `${origin}${API_V1_PREFIX}${suffix}`
}

export const apiErrorMessage = (payload: unknown, fallback = 'Request failed.'): string => {
  const error = (payload as ApiErrorPayload)?.error
  if (typeof error === 'object' && typeof error?.message === 'string' && error.message) {
    return error.message
  }
  if (typeof error === 'string' && error) return error
  return fallback
}

export const unwrap = async <T>(parsed: Promise<T>): Promise<T> => {
  const data = await parsed
  if ((data as { error?: unknown })?.error) {
    // Once the signed-out modal owns the screen, every in-flight call fails for the same
    // reason. Never settling leaves callers in their loading state rather than painting
    // error text behind the modal; the page is about to be replaced by a fresh sign-in.
    if (isSignedOut()) return new Promise<T>(() => {})
    throw new Error(apiErrorMessage(data as ApiErrorPayload))
  }
  return data
}

export const isSessionExpired = async (response: Response) => {
  // Only the auth guard sends this code. A wrong password on login or on a password
  // change also answers 401, but with `invalid_credentials` - that is a failed attempt,
  // not a session that stopped working underneath the user.
  if (response?.status !== 401) return false
  try {
    const body = (await response.clone().json<boolean>()) as Partial<ErrorResponse>
    return body?.error?.code === 'authentication_required'
  } catch {
    return false
  }
}

export const request = ky.create({
  prefix: API_V1_PREFIX,
  throwHttpErrors: false,
  // ky's default is 10s; some admin operations (git/mariadb checks) can
  // legitimately run longer than that, well under nginx/gunicorn's 120s ceiling.
  timeout: 60_000,
  hooks: {
    // ky 2.x passes a single state object. Returning nothing leaves the response untouched.
    afterResponse: [
      async ({ response }) => {
        if (await isSessionExpired(response)) reportSignedOut()
      },
    ],
  },
})
