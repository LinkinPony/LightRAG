import { useEffect, useMemo, useState } from 'react'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'
import Separator from '@/components/ui/Separator'
import type { TagEquals, TagIn } from '@/contexts/types'
import { useTranslation } from 'react-i18next'

type EqEntry = { key: string; value: string }
type InEntry = { key: string; values: string[] }

function toEqEntries(map?: TagEquals): EqEntry[] {
  if (!map) return []
  return Object.entries(map).map(([k, v]) => ({ key: k, value: v }))
}

function toInEntries(map?: TagIn): InEntry[] {
  if (!map) return []
  return Object.entries(map).map(([k, v]) => ({ key: k, values: v }))
}

function eqToMap(entries: EqEntry[]): TagEquals {
  const out: TagEquals = {}
  for (const e of entries) {
    const k = e.key.trim()
    const v = e.value.trim()
    if (k && v) out[k] = v
  }
  return out
}

function inToMap(entries: InEntry[]): TagIn {
  const out: TagIn = {}
  for (const e of entries) {
    const k = e.key.trim()
    const vals = Array.from(new Set(e.values.map((x) => (x ?? '').trim()).filter((x) => x.length > 0)))
    if (k && vals.length > 0) out[k] = vals
  }
  return out
}

export default function TagFilterEditor({
  value,
  onChange
}: {
  value?: { tag_equals?: TagEquals; tag_in?: TagIn }
  onChange?: (next: { tag_equals?: TagEquals; tag_in?: TagIn }) => void
}) {
  const { t } = useTranslation()
  const [eqEntries, setEqEntries] = useState<EqEntry[]>(() => toEqEntries(value?.tag_equals))
  const [inEntries, setInEntries] = useState<InEntry[]>(() => toInEntries(value?.tag_in))

  const sync = (nextEq: EqEntry[], nextIn: InEntry[]) => {
    setEqEntries(nextEq)
    setInEntries(nextIn)
    const eqMap = eqToMap(nextEq)
    const inMap = inToMap(nextIn)
    onChange?.({ tag_equals: Object.keys(eqMap).length ? eqMap : undefined, tag_in: Object.keys(inMap).length ? inMap : undefined })
  }

  const addEq = () => sync([...eqEntries, { key: '', value: '' }], inEntries)
  const removeEq = (idx: number) => sync(eqEntries.filter((_, i) => i !== idx), inEntries)
  const setEqKey = (idx: number, key: string) => {
    const next = eqEntries.slice()
    next[idx] = { ...next[idx], key }
    sync(next, inEntries)
  }
  const setEqValue = (idx: number, value: string) => {
    const next = eqEntries.slice()
    next[idx] = { ...next[idx], value }
    sync(next, inEntries)
  }

  const addIn = () => sync(eqEntries, [...inEntries, { key: '', values: [''] }])
  const removeIn = (idx: number) => sync(eqEntries, inEntries.filter((_, i) => i !== idx))
  const setInKey = (idx: number, key: string) => {
    const next = inEntries.slice()
    next[idx] = { ...next[idx], key }
    sync(eqEntries, next)
  }
  const setInValue = (idx: number, vIdx: number, val: string) => {
    const next = inEntries.slice()
    const values = next[idx].values.slice()
    values[vIdx] = val
    next[idx] = { ...next[idx], values }
    sync(eqEntries, next)
  }
  const addInValue = (idx: number) => {
    const next = inEntries.slice()
    const values = next[idx].values.slice()
    values.push('')
    next[idx] = { ...next[idx], values }
    sync(eqEntries, next)
  }
  const removeInValue = (idx: number, vIdx: number) => {
    const next = inEntries.slice()
    const values = next[idx].values.filter((_, i) => i !== vIdx)
    next[idx] = { ...next[idx], values: values.length > 0 ? values : [''] }
    sync(eqEntries, next)
  }

  // Keep internal state in sync with external value, but avoid wiping local editing rows
  useEffect(() => {
    const currentEqMap = eqToMap(eqEntries)
    const nextEqMap = value?.tag_equals ?? {}
    const currentInMap = inToMap(inEntries)
    const nextInMap = value?.tag_in ?? {}

    const eqSame = JSON.stringify(currentEqMap) === JSON.stringify(nextEqMap)
    const inSame = JSON.stringify(currentInMap) === JSON.stringify(nextInMap)

    if (!eqSame) {
      setEqEntries(toEqEntries(value?.tag_equals))
    }
    if (!inSame) {
      setInEntries(toInEntries(value?.tag_in))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value?.tag_equals, value?.tag_in])

  return (
    <div className="space-y-4">
      <div>
        <div className="font-medium text-sm mb-2">{t('tags.filter.equals')}</div>
        <div className="space-y-2">
          {eqEntries.length === 0 && (
            <div className="text-xs text-gray-500">No equals filters. Click "Add key".</div>
          )}
          {eqEntries.map((e, idx) => (
            <div key={`eq-${idx}`} className="flex items-center gap-2">
              <Input
                value={e.key}
                onChange={(ev: React.ChangeEvent<HTMLInputElement>) => setEqKey(idx, ev.target.value)}
                placeholder={t('tags.key')}
                className="w-40"
              />
              <Input
                value={e.value}
                onChange={(ev: React.ChangeEvent<HTMLInputElement>) => setEqValue(idx, ev.target.value)}
                placeholder={t('tags.value')}
                className="flex-1"
              />
              <Button size="sm" variant="ghost" onClick={() => removeEq(idx)}>{t('tags.remove')}</Button>
            </div>
          ))}
          <Button size="sm" variant="outline" onClick={addEq}>{t('tags.addKey')}</Button>
        </div>
      </div>
      <Separator />
      <div>
        <div className="font-medium text-sm mb-2">{t('tags.filter.in')}</div>
        <div className="space-y-2">
          {inEntries.length === 0 && (
            <div className="text-xs text-gray-500">No in filters. Click "Add key".</div>
          )}
          {inEntries.map((e, idx) => (
            <div key={`in-${idx}`} className="border rounded-md p-2 space-y-2">
              <div className="flex items-center gap-2">
                <Input
                  value={e.key}
                  onChange={(ev: React.ChangeEvent<HTMLInputElement>) => setInKey(idx, ev.target.value)}
                  placeholder={t('tags.key')}
                  className="w-40"
                />
                <Button size="sm" variant="ghost" onClick={() => removeIn(idx)}>{t('tags.remove')}</Button>
              </div>
              <div className="space-y-2">
                {e.values.map((v, vIdx) => (
                  <div key={`in-${idx}-v-${vIdx}`} className="flex items-center gap-2">
                    <Input
                      value={v}
                      onChange={(ev: React.ChangeEvent<HTMLInputElement>) => setInValue(idx, vIdx, ev.target.value)}
                      placeholder={t('tags.value')}
                      className="flex-1"
                    />
                    <Button size="sm" variant="ghost" onClick={() => removeInValue(idx, vIdx)}>{t('tags.remove')}</Button>
                  </div>
                ))}
                <Button size="sm" variant="outline" onClick={() => addInValue(idx)}>{t('tags.addValue')}</Button>
              </div>
            </div>
          ))}
          <Button size="sm" variant="outline" onClick={addIn}>{t('tags.addKey')}</Button>
        </div>
      </div>
    </div>
  )
}


