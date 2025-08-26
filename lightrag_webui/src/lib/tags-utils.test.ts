import { describe, it, expect } from 'bun:test'
import { buildInsertPayload, buildQueryParams, cleanTagEquals, cleanTagIn, cleanTagMap } from '@/lib/utils'

describe('Tag Plan C - cleaning helpers', () => {
  it('cleanTagMap should trim keys, drop empty, dedupe arrays', () => {
    const input = {
      ' project ': ' alpha ',
      emptyKey: '   ',
      owner: [' alice ', 'bob', ' ', 'alice'],
      invalid: 123,
    } as any
    const cleaned = cleanTagMap(input)!
    expect(cleaned).toEqual({ project: 'alpha', owner: ['alice', 'bob'] })
  })

  it('cleanTagMap returns undefined when nothing valid', () => {
    expect(cleanTagMap(undefined)).toBeUndefined()
    expect(cleanTagMap({ a: '   ', b: [] })).toBeUndefined()
  })

  it('cleanTagEquals should only keep non-empty string values', () => {
    const cleaned = cleanTagEquals({ x: ' A ', y: '  ', z: ['bad'] } as any)!
    expect(cleaned).toEqual({ x: 'A' })
  })

  it('cleanTagIn should only keep non-empty string arrays (deduped)', () => {
    const cleaned = cleanTagIn({ owners: [' a ', 'b', 'a', ' '], bad: 'x' } as any)!
    expect(cleaned).toEqual({ owners: ['a', 'b'] })
  })
})

describe('Tag Plan C - payload builders', () => {
  it('buildInsertPayload includes only non-empty fields', () => {
    const payload = buildInsertPayload({
      text: ' hello ',
      file_source: '  src.txt  ',
      tags: { lang: ' en ', team: [' a ', 'b', 'a', ' '] },
    })
    expect(payload).toEqual({
      text: ' hello ',
      file_source: 'src.txt',
      tags: { lang: 'en', team: ['a', 'b'] },
    })

    const empty = buildInsertPayload({ text: 'x', file_source: '   ', tags: { a: '  ' } })
    expect(empty).toEqual({ text: 'x' })
  })

  it('buildQueryParams adds tag filters only when non-empty', () => {
    const base = { query: 'Q', mode: 'naive' }
    const out1 = buildQueryParams(base, { tag_equals: { project: ' alpha ' }, tag_in: { owner: [' a ', ' '] } })
    expect(out1).toEqual({ query: 'Q', mode: 'naive', tag_equals: { project: 'alpha' }, tag_in: { owner: ['a'] } })

    const out2 = buildQueryParams(base, { tag_equals: { x: '   ' }, tag_in: { y: [] } })
    expect(out2).toEqual({ query: 'Q', mode: 'naive' })
  })
})



