import { render, screen } from '@testing-library/react'
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
    expect(screen.getByText('通胀')).toBeInTheDocument()
    expect(screen.getByText('美元')).toBeInTheDocument()
    expect(screen.queryByText('跨资产传导')).not.toBeInTheDocument()
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
  it('将日期与事件放在同一个复盘时间轴中', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: '历史复盘' }))

    expect(screen.getByRole('heading', { name: '日期与事件复盘' })).toBeInTheDocument()
    expect(screen.getByLabelText('选择日期')).toBeInTheDocument()
    expect(screen.getByLabelText('搜索事件')).toBeInTheDocument()
    for (const step of ['事前背景', '当时信息集', '事件发生', '即时反应', '后续演化', '复盘结论']) {
      expect(screen.getByText(step)).toBeInTheDocument()
    }
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
