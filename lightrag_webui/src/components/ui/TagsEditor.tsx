import { useEffect, useState } from 'react'
import Input from '@/components/ui/Input'
import Button from '@/components/ui/Button'
import Checkbox from '@/components/ui/Checkbox'
import Separator from '@/components/ui/Separator'
import type { TagMap } from '@/contexts/types'

type TagEntry = {
  key: string
  isMulti: boolean
  values: string[]
}

function toEntries(map: TagMap | undefined): TagEntry[] {
  if (!map) return []
  const entries: TagEntry[] = []
  for (const [k, v] of Object.entries(map)) {
    if (Array.isArray(v)) {
      entries.push({ key: k, isMulti: true, values: v })
    } else {
      entries.push({ key: k, isMulti: false, values: [v] })
    }
  }
  return entries
}

function toMap(entries: TagEntry[]): TagMap {
  const out: TagMap = {}
  for (const e of entries) {
    const key = e.key
    if (!key.trim()) continue
    const cleaned = e.values.map((x) => x ?? '').map((x) => x.trim()).filter((x) => x.length > 0)
    if (cleaned.length === 0) continue
    out[key] = e.isMulti ? Array.from(new Set(cleaned)) : cleaned[0]
  }
  return out
}

export default function TagsEditor({
  value,
  onChange
}: {
  value?: TagMap
  onChange?: (next: TagMap | undefined) => void
}) {
  const [entries, setEntries] = useState<TagEntry[]>(() => toEntries(value))

  const stringifyNormalized = (map: TagMap | undefined) => {
    if (!map) return ''
    const normalized: Record<string, string | string[]> = {}
    const keys = Object.keys(map).sort()
    for (const k of keys) {
      const v = map[k]
      if (Array.isArray(v)) {
        normalized[k] = [...v].sort()
      } else {
        normalized[k] = v
      }
    }
    return JSON.stringify(normalized)
  }

  const handleSync = (next: TagEntry[]) => {
    setEntries(next)
    const mapped = toMap(next)
    const mappedOrUndef = Object.keys(mapped).length > 0 ? mapped : undefined
    // Avoid triggering parent update if nothing semantically changed
    const currentNormalized = stringifyNormalized(value)
    const nextNormalized = stringifyNormalized(mappedOrUndef)
    if (currentNormalized === nextNormalized) return
    onChange?.(mappedOrUndef)
  }

  const addKey = () => {
    const next = [...entries, { key: '', isMulti: false, values: [''] }]
    handleSync(next)
  }

  const removeKey = (idx: number) => {
    const next = entries.filter((_, i) => i !== idx)
    handleSync(next)
  }

  const setKey = (idx: number, key: string) => {
    const next = entries.slice()
    next[idx] = { ...next[idx], key }
    handleSync(next)
  }

  const toggleMulti = (idx: number, isMulti: boolean) => {
    const next = entries.slice()
    const current = next[idx]
    if (!isMulti && current.values.length > 1) {
      // collapse to single
      next[idx] = { ...current, isMulti: false, values: [current.values[0] ?? ''] }
    } else if (isMulti && current.values.length === 0) {
      next[idx] = { ...current, isMulti: true, values: [''] }
    } else {
      next[idx] = { ...current, isMulti }
    }
    handleSync(next)
  }

  const setValue = (idx: number, vIdx: number, val: string) => {
    const next = entries.slice()
    const values = next[idx].values.slice()
    values[vIdx] = val
    next[idx] = { ...next[idx], values }
    handleSync(next)
  }

  const addValue = (idx: number) => {
    const next = entries.slice()
    const values = next[idx].values.slice()
    values.push('')
    next[idx] = { ...next[idx], values }
    handleSync(next)
  }

  const removeValue = (idx: number, vIdx: number) => {
    const next = entries.slice()
    const values = next[idx].values.filter((_, i) => i !== vIdx)
    next[idx] = { ...next[idx], values: values.length > 0 ? values : [''] }
    handleSync(next)
  }

  // Keep internal state in sync if parent value changes identity
  useEffect(() => {
    setEntries(toEntries(value))
  }, [value])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="font-medium text-sm">Tags</div>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={addKey}>Add key</Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => handleSync([])}
          >
            Clear
          </Button>
        </div>
      </div>
      <Separator />
      <div className="space-y-3">
        {entries.length === 0 && (
          <div className="text-xs text-gray-500">No tags. Click "Add key" to start.</div>
        )}
        {entries.map((entry, idx) => (
          <div key={idx} className="border rounded-md p-3 space-y-2">
            <div className="flex items-center gap-2">
              <div className="text-xs text-gray-500 w-16">Key</div>
              <Input
                value={entry.key}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setKey(idx, e.target.value)}
                placeholder="e.g. project"
                className="flex-1"
              />
              <Checkbox
                checked={entry.isMulti}
                onCheckedChange={(checked) => toggleMulti(idx, checked === true)}
              />
              <span className="text-xs text-gray-500 select-none">Multiple</span>
              <Button size="sm" variant="outline" onClick={() => removeKey(idx)}>Remove</Button>
            </div>
            <div className="space-y-2">
              {entry.isMulti ? (
                <div className="space-y-2">
                  {entry.values.map((v, vIdx) => (
                    <div key={vIdx} className="flex items-center gap-2">
                      <div className="text-xs text-gray-500 w-16">Value</div>
                      <Input
                        value={v}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(idx, vIdx, e.target.value)}
                        placeholder="e.g. alice"
                        className="flex-1"
                      />
                      <Button size="sm" variant="ghost" onClick={() => removeValue(idx, vIdx)}>Remove</Button>
                    </div>
                  ))}
                  <div>
                    <Button size="sm" variant="outline" onClick={() => addValue(idx)}>Add value</Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <div className="text-xs text-gray-500 w-16">Value</div>
                  <Input
                    value={entry.values[0] ?? ''}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(idx, 0, e.target.value)}
                    placeholder="e.g. alpha"
                    className="flex-1"
                  />
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}


