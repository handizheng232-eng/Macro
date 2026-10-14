import type { Plugin } from 'vite'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

// Only the two registered macro modules have these archive-only metadata fields.
// Source JSON bytes, economic values, vintages and the three approved replays stay intact.
export function redactArchiveMetadata(source: string, id: string): string | null {
  const path = id.split('?')[0].replace(/\\/g, '/')
  if (!['/src/data/usEmploymentData.json', '/src/data/usLateModulesData.json'].some((suffix) => path.endsWith(suffix))) return null
  const data: unknown = JSON.parse(source)
  if (!isRecord(data) || !isRecord(data.rawSnapshots)) return null
  const snapshots = { ...data.rawSnapshots }
  let changed = false
  for (const [key, value] of Object.entries(snapshots)) {
    if (typeof value === 'string' && /^(?:[A-Za-z]:[\\/]|\\\\|\/home\/|\/Users\/|\/mnt\/)/.test(value)) {
      snapshots[key] = null
      changed = true
    }
  }
  return changed ? JSON.stringify({ ...data, rawSnapshots: snapshots }) : null
}

export function publicArchiveMetadata(): Plugin {
  return {
    name: 'public-archive-metadata',
    enforce: 'pre',
    apply: 'build',
    transform(source, id) {
      const code = redactArchiveMetadata(source, id)
      return code === null ? null : { code, map: null }
    },
  }
}
