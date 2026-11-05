# PCE分项价格涨幅分布

## 展示与口径

位置：美国通胀 → 实际通胀与结构拆分，紧接CPI/PCE总量走势图。

新增100%堆叠柱状图、七档区间、鼠标逐月读数、键盘可操作的月份选择、可展开的数据表。沿用通胀页的卡片、图例和颜色系统；窄屏仅图表及表格局部横向滚动。

- 横轴是观察月份。纵轴是**消费支出权重占比**，不是价格涨幅本身，也不是分项数量占比。
- 按分项**月度环比折年涨幅**分为六档：`≤0`、`(0,2]`、`(2,3]`、`(3,5]`、`(5,10]`、`>10`（单位%）。不称为同比分布。
- 五档正涨幅桶使用达拉斯联储官方分桶表。未上涨桶为100减去这五档的原始权重总和，包含负涨幅和零涨幅。
- 权重采用达拉斯联储发布口径；精确定义及来源链接随数据输出。不能擅自替换为等权、当前月份名义支出占比，或拿加权平均分项涨幅冒充官方Fisher总PCE涨幅。
- 表格和读数显示两位小数；合计用未舍入权重计算，不倒填尾差。
- 最新一期用官方分项明细的涨幅和支出权重逐项重新分桶，核对官方五档及未上涨余项。

## 来源与历史边界

入口：`https://www.dallasfed.org/research/pce`

- 分布：`https://www.dallasfed.org/-/media/documents/research/pce/pcedata.xlsx`
- 分项与权重：`https://www.dallasfed.org/~/media/documents/research/pce/detail`
- 方法：入口页的Calculation、Glossary和Technical documentation。

首次接入时，官方分布下载表覆盖2025-09至2026-09，13个月；分项表仅提供最新一期。另一个`pcehist`文件是截尾均值等汇总通胀率长历史，**不是分布历史**，不得代替或据此推造早期分布。七档区间始终锚定最新真实观察月，超出现有历史的部分不补值。

首次增量接入保留原iFinD序列及其快照时间；Dallas分布另列自己的实际获取时间。后续刷新须同时保留原始官方工作簿、来源身份与SHA，并通过同批时间和分桶闭合校验后才更新数据。

## 验证入口

- 前端：`npm test -- --run src/pceDistribution.test.tsx src/pceDistributionIntegration.test.tsx`
- 类型/样式：`npm run lint`、`npm run build`、`git diff --check`
- 真实浏览器验收脚本：`verify_pce_browser.py`（随本地验收证据归档，不进入公开站点包）。

浏览器验收按桌面/手机分别检查七档日期范围、全部柱面积与源值、逐月表格及月份选择读数、真实指针悬停、刻度/表头对齐、标题控件不重叠，以及整页无横向溢出。脚本输出不等同于已上线；部署状态必须另以精确提交、Pages运行及生产资源实读核验。

## 本次发布合约

- `release/pce-distribution-authorization-01.json` 仅授权本次已审PCE加法扩展与必要测试/发布修复，不升级历史研究完整性，也不授权改写其他宏观数据。
- `scripts/verify_pce_distribution_publish.py` 对现行候选单独验收：完整公开文件及dist清单、原始官方工作簿重放、全部分桶及明细、独立捕获时间、旧iFinD字段完全不变。只去除明确的新增卡片并还原两处来源描述，必须恢复原JSON的全部语义。
- `release/snapshots/macro-pce-baseline-528f3da.zip` 仅含Git中已公开且被上一版本绑定的文件，不含研究原件、会话或`data/raw`。固定SHA的528f3da版本重放原宏观发布门禁；其内部仍重放1a0231d及更早研究门禁。旧回执及旧验证器不改。
- `npm run test:data` 分别执行当前数据测试、3个旧宏观发布测试、40个历史研究发布测试；发现与执行用例数必须一致，且无skip。旧测试在自己的精确公开版本上原样执行，不拿旧数据替代当前PCE数据测试。
- 完整前端发布门禁沿用原CI命令 `npm test -- --testTimeout=12000 --maxWorkers=1`；本地默认5秒结果另行保留，不能把失败说成通过，也不修改原CI预算。
- 公开原始工作簿fixture的JSON外壳保留原字节（`.gitattributes`的`-text`规则）；正式通胀输出统一LF。数据覆写先备份并核验原字节，再原子替换。旧`--input`缺`__pceDistribution`时拒绝输出，防止把新卡片静默删掉。
- 构建后运行 `python -B scripts/verify_pce_distribution_publish.py --legacy-tests --dist dist`。暂存后核对Git blob与回执原字节，再提交推送；成功上线还须精确SHA的Pages成功、生产资源逐字节比对、桌面/手机交互和九模块回归实读。
