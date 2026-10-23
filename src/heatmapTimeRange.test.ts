import { expect, it } from 'vitest'
import { heatmapPeriodIndices, completePeriodMean } from './heatmapTimeRange'

it('按最新观察月回溯12/36个月，支持降序及短历史，不用系统日期', () => {
  const periods = Array.from({ length: 60 }, (_, index) => {
    const d = new Date(Date.UTC(2026, 8 - index, 1))
    return `${d.getUTCFullYear()}${String(d.getUTCMonth() + 1).padStart(2, '0')}`
  })
  expect(heatmapPeriodIndices(periods, '1Y')).toHaveLength(12)
  expect(heatmapPeriodIndices(periods, '3Y')).toHaveLength(36)
  expect(heatmapPeriodIndices(periods, '30Y')).toHaveLength(60)
  expect(heatmapPeriodIndices(periods, 'ALL')).toHaveLength(60)
  expect(heatmapPeriodIndices([], '1Y')).toEqual([])
  expect(heatmapPeriodIndices(['202509', '202609', '202510'], '1Y')).toEqual([1, 2])
})

it('缺失月不得压缩均值分母；完整月均正常计算', () => {
  expect(completePeriodMean([1, 2, 3])).toBe(2)
  expect(completePeriodMean([1, null, 3])).toBeNull()
  expect(completePeriodMean([])).toBeNull()
})
