import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
// Note: type-only import may be unavailable in our current setup; use any to avoid compile issues
import type { InsertPayload, QueryParam, TagEquals, TagIn, TagMap } from '@/contexts/types'

export function cn(...inputs: any[]) {
  return twMerge(clsx(...inputs))
}

export function randomColor() {
  const digits = '0123456789abcdef'
  let code = '#'
  for (let i = 0; i < 6; i++) {
    code += digits.charAt(Math.floor(Math.random() * 16))
  }
  return code
}

export function errorMessage(error: any) {
  return error instanceof Error ? error.message : `${error}`
}

/**
 * Creates a throttled function that limits how often the original function can be called
 * @param fn The function to throttle
 * @param delay The delay in milliseconds
 * @returns A throttled version of the function
 */
export function throttle<T extends (...args: any[]) => any>(fn: T, delay: number): (...args: Parameters<T>) => void {
  let lastCall = 0
  let timeoutId: ReturnType<typeof setTimeout> | null = null

  return function(this: any, ...args: Parameters<T>) {
    const now = Date.now()
    const remaining = delay - (now - lastCall)

    if (remaining <= 0) {
      // If enough time has passed, execute the function immediately
      if (timeoutId) {
        clearTimeout(timeoutId)
        timeoutId = null
      }
      lastCall = now
      fn.apply(this, args)
    } else if (!timeoutId) {
      // If not enough time has passed, set a timeout to execute after the remaining time
      timeoutId = setTimeout(() => {
        lastCall = Date.now()
        timeoutId = null
        fn.apply(this, args)
      }, remaining)
    }
  }
}

type WithSelectors<S> = S extends { getState: () => infer T }
  ? S & { use: { [K in keyof T]: () => T[K] } }
  : never

export const createSelectors = <S extends any>(_store: S) => {
  const store = _store as any
  store.use = {}
  const state: Record<string, unknown> = typeof store.getState === 'function' ? (store.getState() as any) : {}
  for (const k of Object.keys(state)) {
    store.use[k] = () => store((s: any) => s[k as keyof typeof s])
  }
  return store as WithSelectors<typeof _store>
}

// --------------------------
// Tag Plan C - cleaning utils
// --------------------------

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function cleanKey(key: string): string | null {
  const trimmed = key.trim()
  return trimmed.length > 0 ? trimmed : null
}

function cleanStringValue(value: string): string | null {
  const trimmed = value.trim()
  return trimmed.length > 0 ? trimmed : null
}

function cleanStringArray(values: unknown): string[] | null {
  if (!Array.isArray(values)) return null
  const cleaned = Array.from(
    new Set(
      values
        .map((v) => (typeof v === 'string' ? v.trim() : ''))
        .filter((v) => v.length > 0)
    )
  )
  return cleaned.length > 0 ? cleaned : null
}

export function cleanTagMap(input: unknown): TagMap | undefined {
  if (!input || typeof input !== 'object') return undefined
  const map = input as Record<string, unknown>
  const result: TagMap = {}
  for (const [rawKey, rawValue] of Object.entries(map)) {
    const key = cleanKey(rawKey)
    if (!key) continue
    if (typeof rawValue === 'string') {
      const v = cleanStringValue(rawValue)
      if (v) result[key] = v
    } else if (Array.isArray(rawValue)) {
      const arr = cleanStringArray(rawValue)
      if (arr) result[key] = arr
    }
  }
  return Object.keys(result).length > 0 ? result : undefined
}

export function cleanTagEquals(input: unknown): TagEquals | undefined {
  if (!input || typeof input !== 'object') return undefined
  const map = input as Record<string, unknown>
  const result: TagEquals = {}
  for (const [rawKey, rawValue] of Object.entries(map)) {
    const key = cleanKey(rawKey)
    if (!key) continue
    if (typeof rawValue === 'string') {
      const v = cleanStringValue(rawValue)
      if (v) result[key] = v
    }
  }
  return Object.keys(result).length > 0 ? result : undefined
}

export function cleanTagIn(input: unknown): TagIn | undefined {
  if (!input || typeof input !== 'object') return undefined
  const map = input as Record<string, unknown>
  const result: TagIn = {}
  for (const [rawKey, rawValue] of Object.entries(map)) {
    const key = cleanKey(rawKey)
    if (!key) continue
    const arr = cleanStringArray(rawValue)
    if (arr) result[key] = arr
  }
  return Object.keys(result).length > 0 ? result : undefined
}

// Builders: only include fields when non-empty after cleaning
export function buildInsertPayload(params: {
  text?: string
  texts?: string[]
  file_source?: string | null
  file_sources?: string[] | null
  tags?: unknown
}): InsertPayload {
  const payload: InsertPayload = {}
  if (isNonEmptyString(params.text ?? '')) payload.text = params.text!
  if (Array.isArray(params.texts) && params.texts.length > 0) payload.texts = params.texts
  if (typeof params.file_source === 'string') {
    const v = cleanStringValue(params.file_source)
    if (v !== null) payload.file_source = v
  }
  if (Array.isArray(params.file_sources)) {
    const v = cleanStringArray(params.file_sources)
    if (v) payload.file_sources = v
  }
  const tags = cleanTagMap(params.tags)
  if (tags) payload.tags = tags
  return payload
}

export function buildQueryParams(base: Record<string, any>, tagFilters?: { tag_equals?: unknown; tag_in?: unknown }): QueryParam & Record<string, any> {
  const out: Record<string, any> = { ...base }
  const equals = cleanTagEquals(tagFilters?.tag_equals)
  const inMap = cleanTagIn(tagFilters?.tag_in)
  if (equals) out.tag_equals = equals
  if (inMap) out.tag_in = inMap
  return out as QueryParam & Record<string, any>
}
