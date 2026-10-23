import { MACRO_TIME_RANGE_OPTIONS, type MacroTimeRange } from './macroTimeRange'

const monthOrdinal = (period: string) => Number(period.slice(0, 4)) * 12 + Number(period.slice(4, 6)) - 1

export function heatmapPeriodIndices(periods: readonly string[], range: MacroTimeRange): number[] {
  if (!periods.length) return []
  const years = MACRO_TIME_RANGE_OPTIONS.find((option) => option.key === range)?.years ?? null
  const latest = Math.max(...periods.map(monthOrdinal))
  const start = years === null ? -Infinity : latest - years * 12 + 1
  return periods.flatMap((period, index) => monthOrdinal(period) >= start ? [index] : [])
}

export function completePeriodMean(values: readonly (number | null)[]): number | null {
  if (!values.length || values.some((value) => value === null || !Number.isFinite(value))) return null
  return values.reduce<number>((sum, value) => sum + (value ?? 0), 0) / values.length
}
