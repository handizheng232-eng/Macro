# 宏观研究工作台

一个面向宏观研究、日常跟踪与历史复盘的精简研究看板。当前版本先搭好信息架构和交互骨架，所有尚未接入的数据均明确标记为“待接入”，不展示虚构指标。

## 页面结构

- **今日总览**：今日结论、宏观事实、市场定价、卖方观点雷达、重点研报
- **宏观框架**：按《美国宏观数据培训【0829定稿】》重构为九个美国模块——就业、通胀、GDP与核算、消费、住房、企业投资、PMI与库存、财政与国债、美联储与金融条件。入口先检查数据的生产端、加工端和定价端；九个模块均已建设深度页，按PPT路线图、数据描述和图例组织研究工作区，并明确区分可定期更新时序、派生指标、事件型数据与静态案例。中国经济及全球金融条件保留一级框架
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

页面使用构建时数据快照，避免在 GitHub Pages 前端暴露数据凭据。就业、通胀、GDP与经济核算、消费，以及第5—9章的住房、企业投资、PMI与库存、财政与国债、美联储与金融条件，均通过本机已登录的 iFinD 客户端会话取数；OpenBB/Wind通用快照继续保留作交叉核验与其他页面使用：

```bash
npm run refresh:us-macro
```

流程先刷新 Wind 明细，再调用 OpenBB 的免密 provider，将原始 OBBject 保存到 `data/raw/openbb-us-macro/`，最终生成 `src/data/usMacroData.json`。OpenBB 当前负责：

- OECD：实际 GDP、失业率、CPI；
- Federal Reserve：专业预测者通胀预期、有效联邦基金利率；
- 与 Wind 重叠的 GDP、失业率、CPI、EFFR 自动做同期差值核验。

第5—9章共接入52条可核验iFinD源序列、30张图：

- 住房：房贷利率与NAHB、许可/开工、单户/多户、新屋/成屋销量、库存月数、FHFA/Case-Shiller及拖欠率；
- 企业投资：核心资本品订单/出货、产能利用率、建筑/设备/知识产权投资、制造业与数据中心建造；
- PMI与库存：ISM总指数与分项、工业生产、订单—库存差、批发/零售库存销售比、地区联储调查与韩国出口；
- 财政与国债：MTS收入/支出/赤字的滚动12个月、净利息/GDP、公众持有债务/GDP、2Y/10Y与10年期拍卖竞拍倍数；
- 美联储与金融条件：EFFR/IORB/SOFR/ON RRP走廊、准备金/ON RRP/TGA、美债/MBS持仓、2Y/10Y、NFCI与广义美元。

五页均附PPT路线图、数据身份证、“数据是什么—怎么读—口径警示”以及不可得项边界。MBA、Zillow/Redfin、云厂商Capex指引、S&P Flash PMI、QRA、FOMC文本与FF期货/OIS等不属于当前自动更新合同的内容均明确标记，不使用相近序列冒充。

就业页按PPT第一章构建CES/CPS、流量数据、工资、经验框架与第三方交叉验证；通胀页按PPT第二章构建总量、结构、中枢、预期、先行指标与情景复盘。两页每张图同样附数据说明和口径警示。

GDP深度页按PPT第三章重构为四组可更新工作区：潜在增速与支出结构、GDP→最终销售→PDFP核心内需、GDP/GDI双核算与名义—实际价格桥、WEI与NBER月度活动拼图；另保留2022H1 advance/third/latest修订案例和季度内信息流。GDPNow、NY Fed Nowcast以及iFinD未检出的NBER两项明确标为未接入，不使用模拟值或近似序列冒充。

消费深度页按PPT第四章重构为“四个驱动轮—官方双轨—三大背离”：11张可更新图覆盖消费占GDP、收入与消费、零售控制组、名义与实际零售、储蓄率、循环信贷与拖欠、服务/耐用品结构以及软硬数据背离。刷卡、TSA、OpenTable、Redbook和密歇根分党派数据因不属于当前iFinD自动更新合同而明确标为未接入；超额储蓄“耗尽日”保留为反事实假设敏感的历史案例，不冒充实时序列。

九个栏目均以 iFinD 经济数据库（EDB）为主要数据源，读取本机 iFinD 客户端的已登录会话直取 HTTP 接口（见 skill `ifind-edb`）。前四章原始响应分别保存在 `data/raw/ifind-us-employment/`、`data/raw/ifind-us-inflation/`、`data/raw/ifind-us-gdp/` 与 `data/raw/ifind-us-consumption/`；第5—9章统一保存在 `data/raw/ifind-us-late-modules/`，页面数据写入 `src/data/usLateModulesData.json`。刷新脚本逐条核对指标码、名称、机构、频率、单位和量级，并检查月/季频缺口；GDP执行三组会计闭合，消费检查控制组与结构份额，第5—9章另检查财政滚动12个月赤字与支出减收入闭合。

单独刷新：

```bash
npm run refresh:us-employment
npm run refresh:us-inflation
npm run refresh:us-gdp
npm run refresh:us-consumption
npm run refresh:us-late-modules
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
