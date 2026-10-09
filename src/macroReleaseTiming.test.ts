import { describe, expect, it } from 'vitest'
import { macroReleaseTiming } from './macroReleaseTiming'

describe('macroReleaseTiming', () => {
  it('标注主要美国宏观指标的典型发布时间，并保留不确定性', () => {
    expect(macroReleaseTiming({ code: 'G002600500', name: '美国:非农就业人数:季调', institution: '美国劳工局' }, '月')).toContain('每月首个周五')
    expect(macroReleaseTiming({ code: 'G002600362', name: '美国:CPI:当月同比', institution: '美国劳工局' }, '月')).toContain('08:30 ET')
    expect(macroReleaseTiming({ code: 'G002599633', name: '美国:GDP:不变价', institution: '美国经济分析局' }, '季')).toContain('季后约30天')
    expect(macroReleaseTiming({ code: 'G002600494', name: '美国:当周初次申请失业金人数', institution: '美国劳工局' }, '周')).toContain('周四')
    expect(macroReleaseTiming({ code: 'UNKNOWN', name: '未知月频指标', institution: '未知机构' }, '月')).toContain('具体日期以发布机构日历为准')
  })
})
