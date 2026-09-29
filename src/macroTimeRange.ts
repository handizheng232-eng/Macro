export type MacroTimeRange = '1Y' | '3Y' | '5Y' | '10Y' | '20Y' | '30Y' | 'ALL'

export const MACRO_TIME_RANGE_OPTIONS: ReadonlyArray<{
  key: MacroTimeRange
  label: string
  years: number | null
}> = [
  { key: '1Y', label: '1年', years: 1 },
  { key: '3Y', label: '3年', years: 3 },
  { key: '5Y', label: '5年', years: 5 },
  { key: '10Y', label: '10年', years: 10 },
  { key: '20Y', label: '20年', years: 20 },
  { key: '30Y', label: '30年', years: 30 },
  { key: 'ALL', label: '全部', years: null },
]

export function macroTimeRangeCutoff(range: MacroTimeRange, latestTimestamp: number): number {
  const years = MACRO_TIME_RANGE_OPTIONS.find((option) => option.key === range)?.years ?? null
  return years === null
    ? Number.NEGATIVE_INFINITY
    : latestTimestamp - years * 365.25 * 24 * 60 * 60 * 1000
}
