import { request, unwrap } from '@/api/client'
import type { AuditPage } from '@/types/settings'

export const auditApi = {
  list: (params: Record<string, string | number>) =>
    unwrap(request.get('audit-events', { searchParams: params }).json<AuditPage>()),
}
