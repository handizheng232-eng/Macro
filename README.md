# 宏观研究工作台

一个面向宏观研究、日常跟踪与历史复盘的精简研究看板。当前版本先搭好信息架构和交互骨架，所有尚未接入的数据均明确标记为“待接入”，不展示虚构指标。

## 页面结构

- **今日总览**：今日结论、宏观事实、市场定价、卖方观点雷达、重点研报
- **宏观框架**：按《美国宏观数据培训【0829定稿】》重构为九个美国模块——就业、通胀、GDP与核算、消费、住房、企业投资、PMI与库存、财政与国债、美联储与金融条件。入口先检查数据的生产端、加工端和定价端；每个模块给出传导链、核心指标、来源、频率和首要陷阱。就业与通胀保留深度页，现有真实序列被拆入对应模块；住房与企业投资在取得可核验序列前只展示指标框架，不生成模拟图表。中国经济及全球金融条件保留一级框架
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

页面使用构建时数据快照，避免在 GitHub Pages 前端暴露数据凭据。消费、PMI、财政和政策继续使用 Wind/OpenBB；就业、通胀以及 GDP 与经济核算深度页通过本机已登录的 iFinD 客户端会话取数：

```bash
npm run refresh:us-macro
```

流程先刷新 Wind 明细，再调用 OpenBB 的免密 provider，将原始 OBBject 保存到 `data/raw/openbb-us-macro/`，最终生成 `src/data/usMacroData.json`。OpenBB 当前负责：

- OECD：实际 GDP、失业率、CPI；
- Federal Reserve：专业预测者通胀预期、有效联邦基金利率；
- 与 Wind 重叠的 GDP、失业率、CPI、EFFR 自动做同期差值核验。

Wind/OpenBB 当前已接入的序列按研究模块重新编排（GDP中的OpenBB/OECD序列仅保留为通用数据集的交叉核验，不再作为GDP深度页主数据）：

- GDP与核算：深度页改用 iFinD EDB；
- 消费：零售销售、个人消费支出；
- PMI与库存：ISM 制造业、制造业生产；
- 财政与国债：财政赤字、联邦消费支出；
- 美联储与金融条件：有效联邦基金利率、美联储总资产。

住房和企业投资已建立传导链与指标字典，但尚未接入可核验序列；页面明确显示数据缺口。就业页按培训PPT第一章重构为五层：CES/CPS官方双调查、JOLTS与申领失业金流量、AHE/ECI/Atlanta三类工资、Okun/失业缺口/贝弗里奇曲线/Sahm四组经验框架、ADP等第三方交叉验证；每张图均附“数据是什么—怎么读—口径警示”，行业表同时给出近12个月与2018—2019基准。通胀页按PPT第二章重构为“总量读数→结构拆分→底层中枢→预期与锚→发布前先行→情景复盘”六层：保留23项温度表和核心三分法，新增CPI/PCE口径桥、中位数与截尾均值、1月残余季节性、密歇根/SCE分歧、5y5y，以及EIA汽油、Manheim二手车、全球供应链压力和油价—滞胀五步判断框架。

GDP深度页按PPT第三章重构为四组可更新工作区：潜在增速与支出结构、GDP→最终销售→PDFP核心内需、GDP/GDI双核算与名义—实际价格桥、WEI与NBER月度活动拼图；另保留2022H1 advance/third/latest修订案例和季度内信息流。GDPNow、NY Fed Nowcast以及iFinD未检出的NBER两项明确标为未接入，不使用模拟值或近似序列冒充。

就业、通胀与GDP栏目均以 iFinD 经济数据库（EDB）为主要数据源，读取本机 iFinD 客户端的已登录会话直取 HTTP 接口（见 skill `ifind-edb`）；原始响应分别保存在 `data/raw/ifind-us-employment/`、`data/raw/ifind-us-inflation/` 与 `data/raw/ifind-us-gdp/`。各序列独立保留观测日期，刷新脚本会核对指标码、名称、频率、单位和量级；GDP脚本另外执行贡献加总、平减指数恒等式和GDP/GDI均值三组会计闭合检查。

单独刷新：

```bash
npm run refresh:us-employment
npm run refresh:us-inflation
npm run refresh:us-gdp
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
