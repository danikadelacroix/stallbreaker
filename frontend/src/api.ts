import type { Day, LateCheck, LogEntry, Precheck, Proposal } from './types'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...init })
  if (!res.ok) {
    // The API explains refusals in a "detail" field; show that when it is there.
    const body = await res.json().catch(() => null)
    const detail = body && typeof body.detail === 'string' ? body.detail : `Request failed (${res.status})`
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}
const post = (body?: unknown): RequestInit => ({ method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const getDay = () => call<Day>('/api/day')
export const setClock = (now_min: number) => call<Day>('/api/clock', post({ now_min }))
export const resetDay = () => call<{ day: Day }>('/api/reset', post()).then((r) => r.day)
export const getLog = () => call<LogEntry[]>('/api/log')
export const reportStall = (ro_id: string, part_id: string, force_source: string | null = null) =>
  call<Proposal>('/api/stalls', post({ ro_id, part_id, force_source }))
export const getProposal = (id: number) => call<Proposal>(`/api/proposals/${id}`)
export const approveProposal = (id: number, option: string) => call<{ day: Day }>(`/api/proposals/${id}/approve`, post({ option })).then((r) => r.day)
export const dismissProposal = (id: number) => call<Day>(`/api/proposals/${id}/dismiss`, post())
export const getPrecheck = () => call<Precheck>('/api/precheck')
export const orderPrecheck = () => call<{ precheck: Precheck; day: Day }>('/api/precheck/order', post())
export const checkLate = (ro_id: string, part_id: string, arrives_min: number) => call<LateCheck>('/api/late/check', post({ ro_id, part_id, arrives_min }))
export const confirmLate = (ro_id: string, part_id: string, arrives_min: number) =>
  call<{ day: Day }>('/api/late/confirm', post({ ro_id, part_id, arrives_min })).then((r) => r.day)

/** Minutes after 08:00 as a clock time, e.g. 150 -> "10:30". */
export function clock(min: number): string {
  const h = 8 + Math.floor(min / 60)
  const m = min % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`
}

/** A length of time in plain words, e.g. 110 -> "1 h 50 min". */
export function span(min: number): string {
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? `${h} h ${m} min` : `${h} h`
}
