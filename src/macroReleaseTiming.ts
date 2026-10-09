export type ReleaseTimingSource = {
  code: string
  name: string
  institution: string
}

const CODE_NOTES: Record<string, string> = {
  G002600500: '就业报告：通常每月首个周五 08:30 ET，发布上月数据',
  G004786716: '就业报告：通常每月首个周五 08:30 ET，发布上月数据',
  G004786717: '就业报告：通常每月首个周五 08:30 ET，发布上月数据',
  G002600502: '就业报告：通常每月首个周五 08:30 ET，发布上月数据',
  G002600494: '初请失业金：通常每周四 08:30 ET，节假日可能顺延',
  G002600496: '续请失业金：通常每周四 08:30 ET，较初请多一周滞后',
  G003049462: 'JOLTS：通常参考月结束约1个月后 10:00 ET',
  G003049448: 'JOLTS：通常参考月结束约1个月后 10:00 ET',
  G003049504: 'JOLTS：通常参考月结束约1个月后 10:00 ET',
  G005316325: 'JOLTS：通常参考月结束约1个月后 10:00 ET',
  G005349364: 'ECI：通常季后约1个月 08:30 ET',
  G005349376: 'ECI：通常季后约1个月 08:30 ET',
  G002600362: 'CPI：通常每月中旬 08:30 ET，发布上月数据',
  G002600363: 'CPI：通常每月中旬 08:30 ET，发布上月数据',
  G002600387: 'CPI：通常每月中旬 08:30 ET，发布上月数据',
  G002600388: 'CPI：通常每月中旬 08:30 ET，发布上月数据',
  G002601508: 'ISM制造业：通常次月首个工作日 10:00 ET',
  G002601511: 'ISM制造业：通常次月首个工作日 10:00 ET',
  G002601513: 'ISM制造业：通常次月首个工作日 10:00 ET',
  G002601514: 'ISM制造业：通常次月首个工作日 10:00 ET',
  G002601515: 'ISM制造业：通常次月首个工作日 10:00 ET',
  G002601517: 'ISM制造业：通常次月首个工作日 10:00 ET',
  G006598549: '工业生产：通常每月中旬 09:15 ET，发布上月数据',
  G002601698: 'Freddie Mac房贷利率：通常每周四发布',
  G019744864: 'NAHB住房市场指数：通常每月中旬 10:00 ET',
  G002601863: '新屋开工与许可：通常每月中旬 08:30 ET',
  G002601889: '新屋开工与许可：通常每月中旬 08:30 ET',
  G002601890: '新屋开工与许可：通常每月中旬 08:30 ET',
  G002601903: '新屋开工与许可：通常每月中旬 08:30 ET',
  G002601721: '新屋销售：通常每月下旬 10:00 ET',
  G002601743: '成屋销售：通常每月下旬 10:00 ET',
  G003590411: 'FHFA房价指数：通常每月最后一个周二 09:00 ET',
  G002601681: 'Case-Shiller房价：通常每月最后一个周二 09:00 ET',
  G002600770: '美债H.15：美国工作日更新，通常约 16:15 ET',
  G002600774: '美债H.15：美国工作日更新，通常约 16:15 ET',
  G026773952: 'EFFR：纽约联储通常下一工作日约 09:00 ET 发布',
  G005226445: 'SOFR：纽约联储通常下一工作日约 08:00 ET 发布',
  G006736804: 'IORB：利率决议生效日更新，时点取决于FOMC决定',
  G010391328: '准备金：美联储H.4.1通常每周四 16:30 ET',
  G025034601: '美联储持有美债：H.4.1通常每周四 16:30 ET',
  G025034584: '美联储持有MBS：H.4.1通常每周四 16:30 ET',
  G006615675: 'TGA：通常随财政部/美联储周度数据更新，具体日期以官方日历为准',
  G006613831: 'ON RRP用量：纽约联储每个操作日公布',
  G006613832: 'ON RRP利率：政策调整日更新',
  G002601592: '月度财政报告MTS：通常次月约第8个工作日 14:00 ET',
  G002601593: '月度财政报告MTS：通常次月约第8个工作日 14:00 ET',
  G002601594: '月度财政报告MTS：通常次月约第8个工作日 14:00 ET',
  G012902021: '美国国债拍卖：按财政部拍卖日程，结果通常 13:00 ET 后公布',
  G012264492: '芝加哥联储NFCI：通常每周三 08:30 CT',
  G002601564: '密歇根消费者调查：初值通常月中周五、终值通常月末周五 10:00 ET',
  G002601565: '咨商会消费者信心：通常每月最后一个周二 10:00 ET',
  G002601177: '消费信贷G.19：通常参考月后约5个工作日 15:00 ET',
}

function containsAny(value: string, fragments: string[]): boolean {
  return fragments.some((fragment) => value.includes(fragment))
}

export function macroReleaseTiming(source: ReleaseTimingSource, frequency: string): string {
  const exact = CODE_NOTES[source.code]
  if (exact) return exact

  const name = source.name
  const institution = source.institution

  if (containsAny(name, ['GDP', 'GDI', '国内采购总额', '最终销售'])) {
    return 'BEA国民账户：advance通常季后约30天 08:30 ET，之后约30天和60天继续修订'
  }
  if (containsAny(name, ['个人消费支出', '个人可支配收入', '个人储蓄'])) {
    return 'BEA个人收入与支出：通常每月末 08:30 ET，发布上月数据'
  }
  if (containsAny(name, ['CPI', '消费者价格指数'])) {
    return 'CPI：通常每月中旬 08:30 ET，发布上月数据'
  }
  if (containsAny(name, ['非农', '失业率', '劳动参与率', '平均时薪', '每周工时'])) {
    return '就业报告：通常每月首个周五 08:30 ET，发布上月数据'
  }
  if (containsAny(name, ['零售和食品服务销售额'])) {
    return '零售销售：通常每月中旬 08:30 ET，发布上月初值'
  }
  if (containsAny(name, ['耐用品', '资本品订单', '资本品出货'])) {
    return '耐用品订单：通常每月下旬 08:30 ET，发布上月初值'
  }
  if (containsAny(name, ['建造支出', '建筑支出'])) {
    return '建造支出：通常次月首个工作日 10:00 ET'
  }
  if (containsAny(name, ['纽约联储制造业'])) {
    return '纽约联储制造业调查：通常每月中旬 08:30 ET'
  }
  if (containsAny(name, ['费城联储制造业'])) {
    return '费城联储制造业调查：通常每月第三个周四 08:30 ET'
  }
  if (containsAny(name, ['韩国:出口'])) {
    return '韩国出口：通常次月1日附近发布，具体时点以韩国官方日历为准'
  }
  if (institution.includes('美国劳工')) {
    return `${frequency}频BLS指标：发布时间依具体项目而异，常见为 08:30 ET；以BLS发布日历为准`
  }
  if (institution.includes('美国经济分析局')) {
    return `${frequency}频BEA指标：通常 08:30 ET 发布；具体日期以BEA发布日历为准`
  }
  if (institution.includes('美国人口普查局')) {
    return `${frequency}频Census指标：常见于 08:30 或 10:00 ET；具体日期以Census发布日历为准`
  }
  if (frequency === '日') return '美国工作日更新；具体时间以发布机构日历为准'
  if (frequency === '周') return '每周更新；具体星期与时间以发布机构日历为准'
  if (frequency === '季') return '季度更新，通常季后数周发布；具体日期以发布机构日历为准'
  if (frequency === '年') return '年度或不定期更新；具体日期以发布机构日历为准'
  return '月度更新；具体日期以发布机构日历为准'
}
