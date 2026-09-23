# 宏观研究工作台

一个面向宏观研究、日常跟踪与历史复盘的精简研究看板。当前版本先搭好信息架构和交互骨架，所有尚未接入的数据均明确标记为“待接入”，不展示虚构指标。

## 页面结构

- **今日总览**：今日结论、宏观事实、市场定价、卖方观点雷达、重点研报
- **宏观框架**：美国增长、就业和政策使用 OpenBB 与 Wind EDB 季节图；通胀页以 iFinD 经济数据库为数据源，拆为实际通胀分项、调查预期和市场隐含定价；中国经济及全球金融条件保留一级框架
- **主题跟踪**：按需建立研究主题，不预设复杂分类
- **历史复盘**：按美元、美债收益率与美联储政策的共同拐点划分近50年宏观阶段；当前先为“降息起步后的双向政策时代”建立细分复盘页
- **数据与方法**：指标口径、研报资料库、数据版本与来源

## 数据原则

1. 事实、卖方观点和内部判断分层展示。
2. 每条数据保留观测期、发布日期、数据版本和抓取时间。
3. 历史复盘只使用所选日期当时已经获得的信息。
4. 数据缺失时显示空状态，不生成装饰性指标或结论。

## 本地运行

```bash
npm install
npm run dev
```

## 刷新美国宏观数据

页面使用构建时数据快照，避免在 GitHub Pages 前端暴露数据凭据。已配置 `wind-mcp-skill` 与本机 OpenBB MCP 后运行：

```bash
npm run refresh:us-macro
```

流程先刷新 Wind 明细，再调用 OpenBB 的免密 provider，将原始 OBBject 保存到 `data/raw/openbb-us-macro/`，最终生成 `src/data/usMacroData.json`。OpenBB 当前负责：

- OECD：实际 GDP、失业率、CPI；
- Federal Reserve：专业预测者通胀预期、有效联邦基金利率；
- 与 Wind 重叠的 GDP、失业率、CPI、EFFR 自动做同期差值核验。

Wind 继续补足制造业、消费、非农行业分项、PCE、资产负债表和财政数据。当前页面包含：

- 增长：实际 GDP、ISM 制造业、制造业生产、零售销售、个人消费支出；
- 就业：劳动参与率、失业率、非农总量与制造业/建筑业/政府/休闲酒店/专业商业服务分项；
- 通胀：CPI 与 PCE 的同比分项（总/核心/食品/能源/商品/服务/住房）、密歇根大学与克利夫兰联储通胀预期、5/7/10/20 年盈亏平衡通胀率；
- 政策：有效联邦基金利率、美联储总资产、财政赤字、联邦消费支出。

通胀栏目以 iFinD 经济数据库（EDB）为数据源，读取本机 iFinD 客户端的登录会话令牌直取 HTTP 接口（见 skill `ifind-edb`），原始响应保存在 `data/raw/ifind-us-inflation/`。各序列独立保留观测日期。单独刷新通胀栏目：

```bash
npm run refresh:us-inflation
```

## 质量检查

```bash
npm test
npm run test:data
npm run lint
npm run build
```

## GitHub Pages

推送到 `main` 后，GitHub Actions 会自动执行 lint、测试和生产构建，并部署至：

**https://handizheng232-eng.github.io/Macro/**

Vite 的部署基路径设置为 `/Macro/`。
