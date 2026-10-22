import { createContext } from 'react'

export interface ReadingItem { id: string; title: string; depth?: number; number?: string }
export const ReadingLabels = createContext<ReadingItem[]>([])
export function numberReadingItems(items: ReadingItem[]): ReadingItem[] {
  const counters: number[] = []
  return items.map(item => {
    if (item.id === 'replay-page-top') return item
    const depth = item.depth || 0
    counters.length = depth + 1
    counters[depth] = (counters[depth] || 0) + 1
    return { ...item, number: counters.join('.') }
  })
}
