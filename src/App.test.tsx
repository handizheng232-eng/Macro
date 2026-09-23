import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

beforeEach(() => {
  window.location.hash = ''
})

describe('页面导航', () => {
  it('可以通过哈希地址直接打开指定页面', () => {
    window.location.hash = '#framework'
    render(<App />)
    expect(screen.getByRole('heading', { name: '宏观框架' })).toBeInTheDocument()
  })
})

describe('今日总览', () => {
  it('以研究闭环而不是日历或主题验证作为首页结构', () => {
    render(<App />)

    expect(screen.getByRole('heading', { name: '今日总览' })).toBeInTheDocument()
    expect(screen.getByText('今日结论')).toBeInTheDocument()
    expect(screen.getByText('宏观事实')).toBeInTheDocument()
    expect(screen.getByText('市场定价')).toBeInTheDocument()
    expect(screen.getByText('卖方观点雷达')).toBeInTheDocument()
    expect(screen.getByText('重点研报')).toBeInTheDocument()
    expect(screen.queryByText('主题验证')).not.toBeInTheDocument()
    expect(screen.queryByText('事件日历')).not.toBeInTheDocument()
  })
})

describe('宏观框架', () => {
  it('聚焦中美基本面以及以美债、通胀和美元为核心的全球金融条件', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '宏观框架' }))

    expect(screen.getByRole('heading', { name: '宏观框架' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '美国经济' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '中国经济' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '全球金融条件' })).toBeInTheDocument()
    expect(screen.getByText('美债利率')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '通胀' })).toBeInTheDocument()
    expect(screen.getByText('美元')).toBeInTheDocument()
    expect(screen.queryByText('跨资产传导')).not.toBeInTheDocument()
  })

  it('为美国增长、就业、通胀和政策分别提供真实数据季节图子页面', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '宏观框架' }))
    expect(screen.getByText('OpenBB 已接入')).toBeInTheDocument()

    const seasonalPages = [
      ['增长', 'us-growth', 5],
      ['就业', 'us-employment', 8],
      ['政策', 'us-policy', 4],
    ] as const

    for (const [label, slug, chartCount] of seasonalPages) {
      await user.click(screen.getByRole('button', { name: `打开美国${label}子页面` }))
      expect(window.location.hash).toBe(`#framework/${slug}`)
      expect(screen.getByRole('heading', { name: `美国${label}` })).toBeInTheDocument()

      const charts = screen.getByRole('region', { name: `美国${label}季节图` })
      expect(within(charts).getAllByRole('img', { name: /季节图/ })).toHaveLength(chartCount)
      expect(within(charts).getAllByText('Wind EDB').length).toBeGreaterThan(0)
      expect(within(charts).getAllByText(/OpenBB/).length).toBeGreaterThan(0)

      if (label === '增长') {
        expect(within(charts).getByText(/与 Wind EDB 同期核验/)).toBeInTheDocument()
        expect(screen.getByText(/OpenBB 与 Wind/)).toBeInTheDocument()
      }

      await user.click(screen.getByRole('button', { name: '返回宏观框架' }))
    }

    await user.click(screen.getByRole('button', { name: '打开美国通胀子页面' }))
    expect(window.location.hash).toBe('#framework/us-inflation')
    expect(screen.getByRole('heading', { name: '美国通胀' })).toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: /折线图/ })).toHaveLength(8)
    const aggregateChart = screen.getByRole('img', { name: 'CPI同比分项折线图' })
    const headlinePath = aggregateChart.querySelector('[data-series-id="cpi_yoy"]')
    expect(headlinePath?.getAttribute('d')?.match(/M/g)?.length).toBeGreaterThan(1)
    expect(within(screen.getByRole('region', { name: '美国通胀状态摘要' })).getAllByRole('article')).toHaveLength(3)
    expect(screen.getByRole('heading', { name: 'CPI分项温度表' })).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: 'CPI分项温度表' })).getAllByRole('row')).toHaveLength(24)
    expect(screen.getByRole('button', { name: '同比' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '季调环比' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '周期与结构：四项统计检验' })).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: '周期与结构：四项统计检验' })).getAllByRole('row')).toHaveLength(4)
    expect(screen.getByRole('heading', { name: 'CPI环比分项贡献' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '超级核心通胀环比' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '工资—劳动成本—超级核心服务' })).toBeInTheDocument()
    expect(screen.getAllByText('周期分项').length).toBeGreaterThan(0)
    expect(screen.getAllByText('结构分项').length).toBeGreaterThan(0)
    expect(screen.getAllByText('iFinD EDB').length).toBeGreaterThan(0)
    expect(screen.getByText(/数据来源：iFinD 经济数据库（EDB）。/)).toBeInTheDocument()
    expect(screen.queryByText(/Wind · 东方证券/)).not.toBeInTheDocument()
  })

  it('通胀图表支持时间范围切换和序列显隐', async () => {
    const user = userEvent.setup()
    window.location.hash = '#framework/us-inflation'
    render(<App />)

    const trendRange = screen.getByRole('group', { name: 'CPI同比分项时间范围' })
    await user.click(within(trendRange).getByRole('button', { name: '1年' }))
    expect(within(trendRange).getByRole('button', { name: '1年' })).toHaveClass('active')

    const trendSeries = screen.getByRole('group', { name: 'CPI同比分项序列开关' })
    const coreCpi = within(trendSeries).getByRole('button', { name: /核心CPI/ })
    expect(coreCpi).toHaveAttribute('aria-pressed', 'true')
    await user.click(coreCpi)
    expect(coreCpi).toHaveAttribute('aria-pressed', 'false')
  })
})

describe('主题跟踪', () => {
  it('以简洁清单开始，并允许按需新增主题', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '主题跟踪' }))
    expect(screen.getByText('尚未建立研究主题')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '新建主题' }))
    await user.type(screen.getByLabelText('主题名称'), '美国财政脉冲')
    await user.click(screen.getByRole('button', { name: '保存主题' }))

    expect(screen.getByRole('heading', { name: '美国财政脉冲' })).toBeInTheDocument()
    expect(screen.queryByText('尚未建立研究主题')).not.toBeInTheDocument()
  })
})

describe('历史复盘', () => {
  it('首页保留十个一级时期，但不再展示日期选择与统一复盘路径', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '历史复盘' }))

    expect(screen.getByRole('heading', { name: '近50年宏观分期' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /宏观阶段：/ })).toHaveLength(10)
    expect(screen.queryByRole('button', { name: /\d{2}期：/ })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('选择日期')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('搜索事件')).not.toBeInTheDocument()
    expect(screen.queryByText('统一复盘路径')).not.toBeInTheDocument()
  })

  it('只为最近阶段提供以特点命名的独立子页面和细分时段', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '历史复盘' }))
    await user.click(screen.getByRole('button', { name: '宏观阶段：降息起步后的双向政策时代' }))
    await user.click(screen.getByRole('button', { name: '进入当前阶段细分复盘' }))

    expect(window.location.hash).toBe('#history/easing-to-tightening')
    expect(screen.getByRole('heading', { name: '降息起步后的双向政策时代' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '返回宏观分期总览' })).toBeInTheDocument()

    const subperiods = screen.getByRole('region', { name: '当前阶段细分时段' })
    expect(within(subperiods).getAllByRole('article')).toHaveLength(5)
    expect(within(subperiods).getByText('2026.09—至今')).toBeInTheDocument()
    expect(within(subperiods).getByRole('heading', { name: '前置式降息' })).toBeInTheDocument()
    expect(within(subperiods).queryByText('10.1')).not.toBeInTheDocument()
  })
})

describe('数据与方法', () => {
  it('集中展示指标口径、研报资料库以及版本来源管理', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '数据与方法' }))

    expect(screen.getByRole('heading', { name: '数据与方法' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '指标口径' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '研报资料库' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '数据版本与来源' })).toBeInTheDocument()
    expect(screen.getByText('观测期')).toBeInTheDocument()
    expect(screen.getByText('发布日期')).toBeInTheDocument()
    expect(screen.getByText('数据版本')).toBeInTheDocument()
  })
})
