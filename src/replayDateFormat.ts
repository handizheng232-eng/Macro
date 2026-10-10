// Reading-layer formatting only. Never use these helpers to persist or filter dates.
const quarters = ['第一', '第二', '第三', '第四']
const separators = /\s*(?:至|—|–|~|～)\s*/
const validDay = (year: number, month: number, day: number) => {
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

export function formatReplayDate(raw: string | null | undefined): string {
  if (!raw) return ''
  const isoRange = /^(\d{4}-\d{2}(?:-\d{2})?|\d{4}-?Q[1-4])\/(\d{4}-\d{2}(?:-\d{2})?|\d{4}-?Q[1-4])$/.exec(raw)
  if (isoRange) return formatReplayDate(`${isoRange[1]}—${isoRange[2]}`)
  const timestamp = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))$/.exec(raw)
  if (timestamp && formatReplayDate(timestamp[1]) !== timestamp[1]) return `${formatReplayDate(timestamp[1])} ${timestamp[2]}`
  const range = raw.split(separators)
  if (range.length === 2) {
    let end = range[1]
    const shortStart = /^(\d{1,2})\/(\d{1,2})$/.exec(range[0])
    if (shortStart && /^\d{1,2}$/.test(end)) end = `${shortStart[1]}/${end}`
    const startLabel = formatReplayDate(range[0]), endLabel = formatReplayDate(end)
    return startLabel !== range[0] && endLabel !== end ? `${startLabel}至${endLabel}` : raw
  }
  const quarter = /^(\d{4})-?Q([1-4])$/i.exec(raw)
  if (quarter) return `${quarter[1]}年${quarters[Number(quarter[2]) - 1]}季度`
  const month = /^(\d{4})-(\d{2})$/.exec(raw)
  if (month && Number(month[2]) >= 1 && Number(month[2]) <= 12) return `${month[1]}年${Number(month[2])}月`
  const day = /^(\d{4})-(\d{2})-(\d{2})$/.exec(raw)
  if (day && validDay(Number(day[1]), Number(day[2]), Number(day[3]))) return `${day[1]}年${Number(day[2])}月${Number(day[3])}日`
  const slash = /^(?:(\d{4})\/)?(\d{1,2})\/(\d{1,2})$/.exec(raw)
  if (slash && validDay(Number(slash[1] || 2000), Number(slash[2]), Number(slash[3]))) return `${slash[1] ? `${slash[1]}年` : ''}${Number(slash[2])}月${Number(slash[3])}日`
  return raw
}

export function formatReplayText(raw: string): string {
  // Protect URLs, filesystem paths, filenames and internal ASCII identifiers before
  // considering date tokens. A bare ratio is deliberately not a date in prose.
  return raw.split(/(https?:\/\/[^\s，；。<>]+|[^\s，；。<>]+[\\/][^\s，；。<>]+\.[A-Za-z0-9]+|(?:[A-Za-z]:[\\/]|\.{1,2}\/|\/[A-Za-z_])[^\s，；。<>]+|(?<![A-Za-z0-9])[A-Za-z_][A-Za-z0-9_.:/\\-]*\d[A-Za-z0-9_.:/\\-]*|[A-Za-z0-9_.-]+\/(?:[A-Za-z0-9_.-]+\/)*[A-Za-z0-9_.-]+\.[A-Za-z]+)/g).map((part, index) => {
    if (index % 2) return part
    const iso = '\\d{4}-(?:\\d{2}(?:-\\d{2})?|Q[1-4])|\\d{4}Q[1-4]'
    const range = new RegExp(`(?<![A-Za-z0-9_./\\\\-])((?:${iso})(?:\\s*(?:至|—|–|~|～)\\s*(?:${iso}))?)(?![A-Za-z0-9_./\\\\-])`, 'g')
    const formatted = part.replace(range, date => formatReplayDate(date))
    const slashDate = '(?:\\d{4}/)?\\d{1,2}/\\d{1,2}(?:\\s*(?:至|—|–|~|～)\\s*(?:(?:\\d{4}/)?\\d{1,2}/)?\\d{1,2})?'
    const forbidden = '(?![A-Za-z0-9_./\\\\-]|\\s*(?:年期|比值|分数|比例|概率|倍|得分|评分))'
    const prefix = new RegExp(`((?:日期|会议|报告|公布|发布|发表|公开|披露|召开|截至|截止)\\s*(?:于|在)?\\s*[：:]?\\s*)(${slashDate})${forbidden}`, 'g')
    const suffix = new RegExp(`(?<![A-Za-z0-9_./\\\\-])(${slashDate})(?=\\s*(?:会议|公布|发布|公开|披露|召开))`, 'g')
    return formatted.replace(prefix, (_match, context: string, date: string) => `${context}${formatReplayDate(date)}`).replace(suffix, date => formatReplayDate(date))
  }).join('')
}
