export type UsMacroCategory = 'growth' | 'employment' | 'inflation' | 'policy'

export const US_MACRO_PAGES = [
  { category: 'growth' as const, slug: 'us-growth', label: '增长', detail: 'GDP · 制造业 · 消费' },
  { category: 'employment' as const, slug: 'us-employment', label: '就业', detail: '参与率 · 失业 · 非农分项' },
  { category: 'inflation' as const, slug: 'us-inflation', label: '通胀', detail: 'CPI · PCE · 通胀预期' },
  { category: 'policy' as const, slug: 'us-policy', label: '政策', detail: '政策利率 · 联储资产 · 财政' },
]

export function categoryFromFrameworkHash(hash: string): UsMacroCategory | null {
  const slug = hash.replace(/^#framework\/?/, '')
  return US_MACRO_PAGES.find((page) => page.slug === slug)?.category ?? null
}

export function frameworkSlug(category: UsMacroCategory): string {
  return US_MACRO_PAGES.find((page) => page.category === category)?.slug ?? 'us-growth'
}
