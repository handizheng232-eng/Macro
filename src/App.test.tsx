import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'

beforeEach(() => {
  window.location.hash = ''
})

describe('页面导航', () => {
  it('浏览器前进后退事件会同步当前哈希页面', () => {
    window.location.hash = '#framework/us-housing'
    render(<App />)
    expect(screen.getByRole('heading', { name: '美国住房' })).toBeInTheDocument()

    window.history.pushState(null, '', '#methods')
    act(() => window.dispatchEvent(new PopStateEvent('popstate')))

    expect(screen.getByRole('heading', { name: '数据与方法' })).toBeInTheDocument()
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
  it('按培训材料的生产端、加工端、定价端组织九个美国宏观模块', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '宏观框架' }))

    expect(screen.getByRole('heading', { name: '宏观框架' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '美国宏观九模块' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '中国经济' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '全球金融条件' })).toBeInTheDocument()
    expect(screen.getByText('生产端')).toBeInTheDocument()
    expect(screen.getByText('加工端')).toBeInTheDocument()
    expect(screen.getByText('定价端')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /打开美国.+模块/ })).toHaveLength(9)
    expect(screen.getByText('住房')).toBeInTheDocument()
    expect(screen.getByText('企业投资')).toBeInTheDocument()
    expect(screen.getByText('财政与国债')).toBeInTheDocument()
    expect(screen.queryByText('跨资产传导')).not.toBeInTheDocument()
  })

  it('把现有真实数据拆入GDP、消费、PMI、财政和联储模块', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '宏观框架' }))
    expect(screen.getByText('OpenBB 已接入')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '打开美国消费模块' }))
    expect(window.location.hash).toBe('#framework/us-consumption')
    expect(screen.getByRole('heading', { name: '美国消费' })).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: '美国消费状态摘要' })).getAllByRole('article')).toHaveLength(6)
    expect(within(screen.getByRole('region', { name: '美国消费研究路线图' })).getAllByRole('article')).toHaveLength(5)
    expect(screen.getByRole('table', { name: '消费数据身份证' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '官方快轨：零售销售' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '官方慢轨：个人收支与信用' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '消费结构：体量看服务，波动看耐用品' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '预期与软硬背离' })).toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: /折线图/ })).toHaveLength(11)
    expect(screen.getByRole('heading', { name: '总零售与控制组环比' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '名义零售与CPI实际化零售' })).toBeInTheDocument()
    expect(screen.getAllByText('iFinD EDB').length).toBeGreaterThan(0)
    expect(screen.getByText(/数据来源：iFinD经济数据库（EDB）。/)).toBeInTheDocument()
    expect(within(screen.getByRole('main')).queryByText('数据来源：Wind EDB。')).not.toBeInTheDocument()
    await user.click(screen.getAllByRole('button', { name: '返回宏观框架' })[0])

    const seasonalPages = [
      ['PMI与库存', 'us-pmi', 2],
      ['财政与国债', 'us-fiscal-treasury', 2],
      ['美联储与金融条件', 'us-fed-financial-conditions', 2],
    ] as const

    for (const [label, slug, chartCount] of seasonalPages) {
      await user.click(screen.getByRole('button', { name: `打开美国${label}模块` }))
      expect(window.location.hash).toBe(`#framework/${slug}`)
      expect(screen.getByRole('heading', { name: `美国${label}` })).toBeInTheDocument()

      const charts = screen.getByRole('region', { name: `美国${label}已接入数据` })
      expect(within(charts).getAllByRole('img', { name: /季节图/ })).toHaveLength(chartCount)
      expect(within(charts).getAllByText(/Wind EDB/).length).toBeGreaterThan(0)
      if (['PMI与库存', '财政与国债'].includes(label)) {
        expect(screen.getByText('数据来源：Wind EDB。')).toBeInTheDocument()
        expect(within(screen.getByRole('main')).queryByText(/数据来源：OpenBB/)).not.toBeInTheDocument()
      }

      await user.click(screen.getByRole('button', { name: '返回宏观框架' }))
    }

    await user.click(screen.getByRole('button', { name: '打开美国GDP与核算模块' }))
    expect(window.location.hash).toBe('#framework/us-growth')
    expect(screen.getByRole('heading', { name: '美国GDP与经济核算' })).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: '美国GDP状态摘要' })).getAllByRole('article')).toHaveLength(5)
    expect(within(screen.getByRole('region', { name: 'GDP与经济核算路线图' })).getAllByRole('article')).toHaveLength(5)
    expect(screen.getByRole('table', { name: 'GDP数据身份证' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '潜在增速与支出结构' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '核心GDP与增长贡献' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '收入法与名义—实际桥' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Nowcast与衰退判定' })).toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: /折线图|堆叠柱图/ })).toHaveLength(8)
    expect(screen.getByRole('heading', { name: '实际GDP与CBO潜在GDP' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '从头条GDP剥到私人内需' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '同一经济的支出法与收入法' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'NBER月度活动拼图' })).toBeInTheDocument()
    expect(screen.getAllByText('iFinD EDB').length).toBeGreaterThan(0)
    expect(screen.getByText(/数据来源：iFinD经济数据库（EDB）。/)).toBeInTheDocument()
    expect(within(screen.getByRole('main')).queryByText(/OpenBB · OECD/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '返回宏观框架' }))

    await user.click(screen.getByRole('button', { name: '打开美国就业模块' }))
    expect(window.location.hash).toBe('#framework/us-employment')
    expect(screen.getByRole('heading', { name: '美国就业' })).toBeInTheDocument()
    expect(within(screen.getByRole('region', { name: '美国就业状态摘要' })).getAllByRole('article')).toHaveLength(5)
    expect(within(screen.getByRole('region', { name: '就业数据体系路线图' })).getAllByRole('article')).toHaveLength(5)
    expect(screen.getByRole('heading', { name: '官方双调查' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '流量与周频' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '工资三口径' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '四大经验框架' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '第三方交叉验证' })).toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: /折线图|散点图|堆叠柱图/ })).toHaveLength(21)
    expect(screen.getByRole('table', { name: '行业就业广度与结构表' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: '就业数据身份证' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '新增非农：月度增量与3个月均值' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'U1—U6失业谱系' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'V/U与ECI工资压力' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Sahm规则' })).toBeInTheDocument()
    expect(screen.getAllByText('iFinD EDB').length).toBeGreaterThan(0)
    expect(screen.getByText(/数据来源：iFinD 经济数据库（EDB）。/)).toBeInTheDocument()
    expect(screen.queryByText('Wind EDB')).not.toBeInTheDocument()
    expect(within(screen.getByRole('main')).queryByText(/OpenBB/)).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: '返回宏观框架' }))

    await user.click(screen.getByRole('button', { name: '打开美国通胀模块' }))
    expect(window.location.hash).toBe('#framework/us-inflation')
    expect(screen.getByRole('heading', { name: '美国通胀' })).toBeInTheDocument()
    expect(screen.getAllByRole('img', { name: /折线图|柱状图/ })).toHaveLength(18)
    expect(within(screen.getByRole('region', { name: '通胀研究路线图' })).getAllByRole('article')).toHaveLength(6)
    expect(screen.getByRole('table', { name: 'CPI与PCE数据身份证' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: '通胀指标说明' })).toBeInTheDocument()
    const aggregateChart = screen.getByRole('img', { name: 'CPI同比分项折线图' })
    const headlinePath = aggregateChart.querySelector('[data-series-id="cpi_yoy"]')
    expect(headlinePath?.getAttribute('d')?.match(/M/g)?.length).toBeGreaterThan(1)
    expect(within(screen.getByRole('region', { name: '美国通胀状态摘要' })).getAllByRole('article')).toHaveLength(3)
    expect(screen.getByRole('heading', { name: 'CPI分项温度表' })).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: 'CPI分项温度表' })).getAllByRole('row')).toHaveLength(24)
    expect(screen.getByRole('button', { name: '同比' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '季调环比' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '周期与结构：四项描述性诊断' })).toBeInTheDocument()
    expect(within(screen.getByRole('table', { name: '周期与结构：四项描述性诊断' })).getAllByRole('row')).toHaveLength(4)
    expect(screen.getByRole('heading', { name: 'CPI环比分项贡献' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '超级核心通胀环比' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '工资—劳动成本—超级核心服务' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '商品通胀与服务通胀的分化' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '租金与业主等价租金' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '底层通胀：核心、中位数与截尾均值' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '核心CPI、核心PCE及其差值' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '季调后仍有1月效应' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '特殊分项：先读算法，再读经济' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '两大消费者调查及长期预期' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '5年后5年远期通胀补偿' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '汽油零售价与CPI能源' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Manheim批发价领先CPI二手车' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '供应链压力与核心商品通胀' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '油价冲击：先分一阶、二阶与滞胀条件' })).toBeInTheDocument()
    expect(screen.getAllByText('周期分项').length).toBeGreaterThan(0)
    expect(screen.getAllByText('结构分项').length).toBeGreaterThan(0)
    expect(screen.getAllByText('iFinD EDB').length).toBeGreaterThan(0)
    expect(screen.getByText(/数据来源：iFinD 经济数据库（EDB）。/)).toBeInTheDocument()
    expect(screen.queryByText(/Wind · 东方证券/)).not.toBeInTheDocument()
  }, 20000)

  it('四个深度数据页使用统一的研究文档层级和章节导航', () => {
    const pages = [
      ['#framework/us-growth', '美国GDP与经济核算深度数据页', 'GDP栏目分区'],
      ['#framework/us-employment', '美国就业深度数据页', '就业栏目分区'],
      ['#framework/us-inflation', '美国通胀深度数据页', '通胀栏目分区'],
      ['#framework/us-consumption', '美国消费深度数据页', '消费栏目分区'],
    ] as const

    for (const [hash, documentName, navigationName] of pages) {
      window.location.hash = hash
      const { unmount } = render(<App />)
      const page = screen.getByRole('document', { name: documentName })
      expect(within(page).getByRole('navigation', { name: navigationName })).toBeInTheDocument()
      unmount()
    }
  })

  it('未接入真实序列的住房模块只展示指标链条和缺口，不生成图表', async () => {
    const user = userEvent.setup()
    window.location.hash = '#framework'
    render(<App />)

    await user.click(screen.getByRole('button', { name: '打开美国住房模块' }))
    expect(window.location.hash).toBe('#framework/us-housing')
    expect(screen.getByRole('heading', { name: '美国住房' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '传导链条' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '核心指标字典' })).toBeInTheDocument()
    expect(screen.getByText('尚未接入可核验的住房序列')).toBeInTheDocument()
    expect(screen.queryByRole('img', { name: /季节图/ })).not.toBeInTheDocument()
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
    expect(screen.getByRole('heading', { name: '数据加工四件套' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '市场重要性五因子' })).toBeInTheDocument()
    expect(screen.getAllByRole('row', { name: /指标字典：/ })).toHaveLength(9)
    expect(screen.getByText('调查对象与样本')).toBeInTheDocument()
    expect(screen.getByText('一致预期')).toBeInTheDocument()
    expect(screen.getByText('单位与转换')).toBeInTheDocument()
    expect(screen.getByText('季节调整 SA')).toBeInTheDocument()
    expect(screen.getByText('季环比折年 SAAR')).toBeInTheDocument()
    expect(screen.getByText('预期差与当期主题')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '研报资料库' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '数据版本与来源' })).toBeInTheDocument()
    expect(screen.getByText('观测期')).toBeInTheDocument()
    expect(screen.getByText('发布日期')).toBeInTheDocument()
    expect(screen.getByText('数据版本')).toBeInTheDocument()
  })
})
